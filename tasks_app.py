#!/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
"""Task board desktop companion.

  • Menu-bar icon → left-click opens a popover with the board.
  • Right-click (or ctrl-click) the icon → menu: "Open as floating window", "Quit".
  • Floating window: always-on-top, draggable to any monitor, resizable.
      Its close button HIDES it (reopen from the menu) instead of leaving an
      ugly minimized thumbnail. ⌘Q quits.

Run with the framework Python that has pyobjc:
  /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tasks_app.py
"""
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE / "server.py"
PORT = 3737
URL = f"http://localhost:{PORT}"
POP_W, POP_H = 860, 720
WIN_W, WIN_H = 900, 820

import objc
from Cocoa import (
    NSApplication, NSObject, NSStatusBar, NSVariableStatusItemLength,
    NSPopover, NSViewController, NSMakeRect, NSApp, NSImage,
    NSApplicationActivationPolicyAccessory, NSMenu, NSMenuItem,
    NSWindow, NSScreen, NSBackingStoreBuffered, NSFloatingWindowLevel,
    NSAlert, NSTextField,
)
from WebKit import WKWebView, WKWebViewConfiguration
from Foundation import NSURL, NSURLRequest

NS_ALERT_FIRST_BUTTON = 1000  # NSAlertFirstButtonReturn

# constants (literals to avoid version-specific import names)
POPOVER_TRANSIENT = 1
EDGE_MIN_Y = 1
MASK_LEFT_UP, MASK_RIGHT_UP = 1 << 2, 1 << 4
TYPE_RIGHT_UP = 4
MOD_CONTROL = 1 << 18
STYLE_TITLED, STYLE_CLOSABLE, STYLE_RESIZABLE = 1, 2, 8
VIEW_W_SIZABLE, VIEW_H_SIZABLE = 2, 16
COLLECTION_ALL_SPACES = 1 << 0


def server_running():
    try:
        with socket.create_connection(("127.0.0.1", PORT), 0.3):
            return True
    except OSError:
        return False


def ensure_server():
    if server_running():
        return
    subprocess.Popen([sys.executable, str(SERVER)], cwd=str(HERE),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if server_running():
            return
        time.sleep(0.1)


# WKWebView shows nothing for window.alert/confirm/prompt unless the app provides
# a UI delegate. Without this, JS prompt() returns null and confirm() returns false,
# so "New project…", delete confirmations, and error alerts silently do nothing.
class WebUIDelegate(NSObject):
    def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_completionHandler_(
            self, wv, message, frame, handler):
        try:
            a = NSAlert.alloc().init()
            a.setMessageText_("Tasks")
            a.setInformativeText_(message or "")
            a.addButtonWithTitle_("OK")
            a.runModal()
        finally:
            handler()

    def webView_runJavaScriptConfirmPanelWithMessage_initiatedByFrame_completionHandler_(
            self, wv, message, frame, handler):
        ok = False
        try:
            a = NSAlert.alloc().init()
            a.setMessageText_("Tasks")
            a.setInformativeText_(message or "")
            a.addButtonWithTitle_("OK")
            a.addButtonWithTitle_("Cancel")
            ok = (a.runModal() == NS_ALERT_FIRST_BUTTON)
        finally:
            handler(ok)

    def webView_runJavaScriptTextInputPanelWithPrompt_defaultText_initiatedByFrame_completionHandler_(
            self, wv, prompt, default_text, frame, handler):
        result = None
        try:
            a = NSAlert.alloc().init()
            a.setMessageText_(prompt or "")
            a.addButtonWithTitle_("OK")
            a.addButtonWithTitle_("Cancel")
            tf = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 260, 24))
            tf.setStringValue_(default_text or "")
            a.setAccessoryView_(tf)
            a.window().setInitialFirstResponder_(tf)
            if a.runModal() == NS_ALERT_FIRST_BUTTON:
                result = tf.stringValue()
        finally:
            handler(result)


_ui_delegate = None   # retained for the lifetime of the app


def make_webview(w, h, url=URL):
    global _ui_delegate
    if _ui_delegate is None:
        _ui_delegate = WebUIDelegate.alloc().init()
    cfg = WKWebViewConfiguration.alloc().init()
    wv = WKWebView.alloc().initWithFrame_configuration_(NSMakeRect(0, 0, w, h), cfg)
    wv.setUIDelegate_(_ui_delegate)
    wv.loadRequest_(NSURLRequest.requestWithURL_(NSURL.URLWithString_(url)))
    return wv


def menu_item(title, target, action, key=""):
    it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
    it.setTarget_(target)
    return it


class PopController(NSViewController):
    def loadView(self):
        self._wv = make_webview(POP_W, POP_H)
        self.setView_(self._wv)

    def refresh(self):
        try: self._wv.evaluateJavaScript_completionHandler_("typeof refreshTasks==='function'&&refreshTasks()", None)
        except Exception: pass


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, _note):
        self.window = None
        self.win_wv = None

        # ── menu bar item ──
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.statusItem.setVisible_(True)
        btn = self.statusItem.button()
        btn.setTitle_("✓ Tasks")   # plain text → always visible, never a blank icon
        btn.setToolTip_("Task board — left-click: popover · right-click: menu")
        btn.setTarget_(self)
        btn.setAction_("statusAction:")
        btn.sendActionOn_(MASK_LEFT_UP | MASK_RIGHT_UP)

        # ── right-click menu ──
        self.menu = NSMenu.alloc().init()
        self.menu.addItem_(menu_item("Open as floating window", self, "openFloating:"))
        self.menu.addItem_(NSMenuItem.separatorItem())
        self.menu.addItem_(menu_item("Quit Tasks", self, "quit:", "q"))

        # ── popover ──
        self.popVC = PopController.alloc().init()
        self.popover = NSPopover.alloc().init()
        self.popover.setContentViewController_(self.popVC)
        self.popover.setContentSize_((POP_W, POP_H))
        self.popover.setBehavior_(POPOVER_TRANSIENT)
        self.popover.setAnimates_(True)

        # ── main menu so ⌘Q works when a surface is focused ──
        mainmenu = NSMenu.alloc().init()
        appItem = NSMenuItem.alloc().init()
        mainmenu.addItem_(appItem)
        appMenu = NSMenu.alloc().init()
        appMenu.addItem_(menu_item("Quit Tasks", self, "quit:", "q"))
        appItem.setSubmenu_(appMenu)
        NSApp.setMainMenu_(mainmenu)

        # Open the floating window right away — the reliable surface that always shows.
        self.openFloating_(None)

    # Re-opening the app (double-click / `open`) re-shows the window if it was hidden.
    def applicationShouldHandleReopen_hasVisibleWindows_(self, _app, _flag):
        self.openFloating_(None)
        return True

    # left-click → popover; right/ctrl-click → menu
    def statusAction_(self, sender):
        ev = NSApp.currentEvent()
        right = ev.type() == TYPE_RIGHT_UP or bool(ev.modifierFlags() & MOD_CONTROL)
        if right:
            self.statusItem.setMenu_(self.menu)
            self.statusItem.button().performClick_(None)
            self.statusItem.setMenu_(None)
        else:
            self.togglePopover()

    def togglePopover(self):
        if self.popover.isShown():
            self.popover.performClose_(None)
            return
        self.popVC.refresh()
        btn = self.statusItem.button()
        self.popover.showRelativeToRect_ofView_preferredEdge_(btn.bounds(), btn, EDGE_MIN_Y)
        NSApp.activateIgnoringOtherApps_(True)

    # ── floating window ──
    def openFloating_(self, _sender):
        self.popover.performClose_(None)
        if self.window is None:
            vf = (NSScreen.mainScreen() or NSScreen.screens()[0]).visibleFrame()
            x = vf.origin.x + vf.size.width - WIN_W - 40
            y = vf.origin.y + vf.size.height - WIN_H - 40
            style = STYLE_TITLED | STYLE_CLOSABLE | STYLE_RESIZABLE   # no minimize button
            win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(x, y, WIN_W, WIN_H), style, NSBackingStoreBuffered, False)
            win.setTitle_("Tasks")
            win.setLevel_(NSFloatingWindowLevel)
            win.setCollectionBehavior_(COLLECTION_ALL_SPACES)
            win.setReleasedWhenClosed_(False)
            win.setMinSize_((360, 480))
            win.setDelegate_(self)
            self.win_wv = make_webview(WIN_W, WIN_H, URL + "?window")
            self.win_wv.setAutoresizingMask_(VIEW_W_SIZABLE | VIEW_H_SIZABLE)
            win.contentView().addSubview_(self.win_wv)
            self.window = win
        else:
            try: self.win_wv.evaluateJavaScript_completionHandler_("typeof refreshTasks==='function'&&refreshTasks()", None)
            except Exception: pass
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    # close button hides the window (reopen from the menu) — no ugly minimized thumbnail
    def windowShouldClose_(self, _win):
        self.window.orderOut_(None)
        return False

    def windowDidBecomeKey_(self, _note):
        try: self.win_wv.evaluateJavaScript_completionHandler_("typeof refreshTasks==='function'&&refreshTasks()", None)
        except Exception: pass

    def quit_(self, _sender):
        NSApp.terminate_(None)


def main():
    ensure_server()
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()

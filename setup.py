"""Build a standalone menu-bar app:  python3 setup.py py2app -A
(-A = alias mode: fast, references the source files in place.)"""
from setuptools import setup

setup(
    app=["tasks_app.py"],
    options={"py2app": {
        "argv_emulation": False,
        "plist": {
            "CFBundleName": "Tasks",
            "CFBundleDisplayName": "Tasks",
            "CFBundleIdentifier": "com.example.taskboard",
            "LSUIElement": True,            # menu-bar agent, no Dock icon
            "LSMinimumSystemVersion": "11.0",
        },
    }},
    setup_requires=["py2app"],
)

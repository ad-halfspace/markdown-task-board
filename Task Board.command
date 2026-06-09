#!/bin/bash
# Double-click to open the task board (or re-show it if already running).
DIR="$(cd "$(dirname "$0")" && pwd)"
open "$DIR/dist/Tasks.app"

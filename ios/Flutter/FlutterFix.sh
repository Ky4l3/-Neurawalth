#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."  # ios/
echo "[FlutterFix] pod install --repo-update"
pod install --repo-update



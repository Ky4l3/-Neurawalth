#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/ios"
rm -rf Pods Podfile.lock
pod cache clean --all
pod install --repo-update

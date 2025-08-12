#!/usr/bin/env bash
set -euo pipefail

echo "[verify] Flutter channel and SDK"
flutter --version

echo "[verify] Pub get"
flutter pub get

echo "[verify] iOS pods state"
cd ios
pod --version
pod deintegrate || true
pod install --repo-update
cd - >/dev/null

echo "[verify] GoogleService-Info.plist present?"
test -f ios/Runner/GoogleService-Info.plist && echo "OK" || { echo "Missing ios/Runner/GoogleService-Info.plist"; exit 1; }

echo "[verify] Static checks"
flutter analyze
flutter test || true


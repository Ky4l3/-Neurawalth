#!/bin/bash
set -euxo pipefail

echo "[xcodecloud] Cloning Flutter SDK (stable)"
git clone https://github.com/flutter/flutter.git -b stable --depth 1 "$CI_WORKSPACE/flutter"
export PATH="$CI_WORKSPACE/flutter/bin:$PATH"
echo "[xcodecloud] Flutter doctor"
flutter doctor -v
flutter --version

echo "[xcodecloud] Fetch pub deps"
flutter pub get

echo "[xcodecloud] Precache iOS artifacts"
flutter precache --ios

echo "[xcodecloud] Install CocoaPods"
cd ios
pod repo update
pod install --repo-update
cd ..

echo "[xcodecloud] Done post-clone"



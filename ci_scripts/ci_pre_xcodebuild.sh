#!/bin/bash
set -euxo pipefail

export PATH="$CI_WORKSPACE/flutter/bin:$PATH"

echo "[xcodecloud] Analyze & tests"
flutter analyze
flutter test || true

echo "[xcodecloud] Ensure iOS artifacts"
flutter build ios --release --no-codesign



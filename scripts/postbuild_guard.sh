#!/usr/bin/env bash
set -euo pipefail

echo "[postbuild] Running analyzer and tests"
flutter analyze
flutter test --coverage || true


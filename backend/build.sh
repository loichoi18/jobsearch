#!/usr/bin/env bash
# Render build script: installs Python deps + the Typst binary.
# Render service settings: Build Command = ./build.sh
#                          Env var TYPST_BIN=./bin/typst
set -euo pipefail

pip install -r requirements.txt

TYPST_VERSION="v0.12.0"
mkdir -p ./bin
curl -sL "https://github.com/typst/typst/releases/download/${TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz" \
  | tar -xJ --strip-components=1 -C ./bin "typst-x86_64-unknown-linux-musl/typst"
chmod +x ./bin/typst
./bin/typst --version

#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="$ROOT/runtime/bin:$PATH"
export DYLD_LIBRARY_PATH="$ROOT/runtime/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
export GI_TYPELIB_PATH="$ROOT/runtime/lib/girepository-1.0"
export XDG_DATA_DIRS="$ROOT/runtime/share${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
exec "$ROOT/runtime/bin/python" "$ROOT/app/compress_images_core.py" "$@"

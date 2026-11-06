import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[2]
MACOS_DIR = ROOT / "packaging" / "macos"
BUILD = MACOS_DIR / "build"
APP = BUILD / "Compress Images.app"
CONTENTS = APP / "Contents"
RESOURCES = CONTENTS / "Resources"
RUNTIME_ARCHIVE = BUILD / "runtime.zip"
ARCH = os.environ.get("MACOS_ARCH", "arm64")
VERSION = os.environ.get("APP_VERSION", "0.0.0")


def write_launcher(path: Path) -> None:
    path.write_text(
        """#!/bin/bash
set -e
APP_ROOT=\"$(cd \"$(dirname \"$0\")/../..\" && pwd)\"
export PATH=\"$APP_ROOT/Contents/Resources/runtime/bin:$PATH\"
export DYLD_LIBRARY_PATH=\"$APP_ROOT/Contents/Resources/runtime/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}\"
export GI_TYPELIB_PATH=\"$APP_ROOT/Contents/Resources/runtime/lib/girepository-1.0\"
export XDG_DATA_DIRS=\"$APP_ROOT/Contents/Resources/runtime/share${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}\"
exec \"$APP_ROOT/Contents/Resources/runtime/bin/python\" \"$APP_ROOT/Contents/Resources/app/compress_images_gui.py\"
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_info_plist(path: Path) -> None:
    path.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleDisplayName</key><string>Compress Images</string>
<key>CFBundleExecutable</key><string>CompressImages</string>
<key>CFBundleIdentifier</key><string>com.github.compress-images</string>
<key>CFBundleIconFile</key><string>compress-images.icns</string>
<key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
<key>CFBundleName</key><string>Compress Images</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>{VERSION}</string>
<key>CFBundleVersion</key><string>{VERSION}</string>
<key>LSMinimumSystemVersion</key><string>12.0</string>
</dict></plist>
''',
        encoding="utf-8",
    )


def create_icon() -> None:
    iconset = BUILD / "compress-images.iconset"
    iconset.mkdir(parents=True)
    sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
    }
    for output_name, source_size in sizes.items():
        source = ROOT / "assets" / "icons" / f"compress-images-{source_size}.png"
        shutil.copy2(source, iconset / output_name)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(RESOURCES / "compress-images.icns")], check=True)


def main() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    (RESOURCES / "app").mkdir(parents=True)
    (CONTENTS / "MacOS").mkdir(parents=True)
    # Preserve shared-library symlinks when creating the ZIP runtime bundle.
    subprocess.run(
        ["conda-pack", "-n", "compress-images", "-o", str(RUNTIME_ARCHIVE), "--zip-symlinks"],
        check=True,
    )
    with zipfile.ZipFile(RUNTIME_ARCHIVE) as archive:
        archive.extractall(RESOURCES / "runtime")
    unpack = RESOURCES / "runtime" / "bin" / "conda-unpack"
    subprocess.run([str(unpack)], cwd=RESOURCES / "runtime", check=True)
    shutil.copy2(ROOT / "src" / "compress_images_core.py", RESOURCES / "app" / "compress_images_core.py")
    shutil.copy2(ROOT / "src" / "compress_images_gui.py", RESOURCES / "app" / "compress_images_gui.py")
    shutil.copy2(ROOT / "LICENSE", RESOURCES / "LICENSE.txt")
    write_launcher(CONTENTS / "MacOS" / "CompressImages")
    write_info_plist(CONTENTS / "Info.plist")
    create_icon()
    cli = BUILD / "CompressImagesCLI.command"
    shutil.copy2(MACOS_DIR / "CompressImagesCLI.command", cli)
    cli.chmod(cli.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shutil.copy2(MACOS_DIR / "README.txt", BUILD / "README.txt")
    dmg_root = BUILD / "dmg-root"
    dmg_root.mkdir()
    shutil.copytree(APP, dmg_root / APP.name)
    (dmg_root / "Applications").symlink_to("/Applications")
    shutil.make_archive(str(BUILD / f"compress-images-macos-{ARCH}"), "zip", root_dir=BUILD, base_dir=APP.name)
    print(APP)


if __name__ == "__main__":
    sys.exit(main())

from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "packaging" / "windows" / "build"
APP = BUILD / "CompressImagesPortable"
RUNTIME_ARCHIVE = BUILD / "runtime.zip"


def main() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    (APP / "app").mkdir(parents=True)
    subprocess.run(
        ["conda-pack", "-n", "compress-images", "-o", str(RUNTIME_ARCHIVE)],
        check=True,
    )
    with zipfile.ZipFile(RUNTIME_ARCHIVE) as archive:
        archive.extractall(APP / "runtime")
    unpack = APP / "runtime" / "Scripts" / "conda-unpack.exe"
    subprocess.run([str(unpack)], cwd=APP / "runtime", check=True)
    shutil.copy2(ROOT / "src" / "compress_images_core.py", APP / "app" / "compress_images_core.py")
    shutil.copy2(ROOT / "src" / "compress_images_gui.py", APP / "app" / "compress_images_gui.py")
    windows_files = Path(__file__).parent
    for name in ("CompressImagesGUI.cmd", "CompressImagesCLI.cmd", "README.txt"):
        shutil.copy2(windows_files / name, APP / name)
    archive_path = shutil.make_archive(
        str(BUILD / "compress-images-windows-x64"),
        "zip",
        root_dir=BUILD,
        base_dir="CompressImagesPortable",
    )
    print(archive_path)


if __name__ == "__main__":
    sys.exit(main())

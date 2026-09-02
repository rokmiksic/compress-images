#!/usr/bin/env python3

import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif",
    ".avif",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".jfif",
}
HEIF_EXTENSIONS = {".heic", ".heif", ".avif"}
SKIP_DIR_NAMES = {"compressed", "__pycache__"}
MIN_QUALITY = 45
START_QUALITY = 90
EMERGENCY_MIN_QUALITY = 20
RESIZE_FACTOR = 0.88
MIN_DIMENSION = 64


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="compress-images",
        description=(
            "Batch pretvori slike v JPG in poskrbi, da je vsaka izhodna datoteka "
            "manjsa ali enaka podani velikosti v MB."
        ),
    )
    parser.add_argument(
        "max_size_mb",
        nargs="?",
        help="Najvecja dovoljena velikost posamezne slike v MB, npr. 0.5, 1, 1.5 ali 2",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Preglej tudi podmape in znotraj 'compressed/' ohrani strukturo map.",
    )
    parser.add_argument(
        "--format",
        choices=("jpg", "webp", "avif", "png"),
        default="jpg",
        help="Izhodni format: jpg, webp, avif ali png (privzeto: jpg).",
    )
    return parser.parse_args()


def parse_size_mb(raw: str) -> float:
    value = raw.strip().replace(",", ".")
    try:
        size_mb = float(value)
    except ValueError as exc:
        raise ValueError("Vnesi veljavno decimalno stevilo, npr. 0.5, 1 ali 1.5.") from exc
    if not math.isfinite(size_mb) or size_mb <= 0:
        raise ValueError("Velikost mora biti pozitivno stevilo, vecje od 0.")
    return size_mb


def prompt_for_size_mb() -> float:
    while True:
        raw = input("Najvecja dovoljena velikost posamezne slike v MB: ").strip()
        try:
            return parse_size_mb(raw)
        except ValueError as exc:
            print(f"Napaka: {exc}", file=sys.stderr)


def ensure_dependencies() -> None:
    required = ["python3", "magick", "identify"]
    missing = [name for name in required if shutil.which(name) is None]
    if missing:
        names = ", ".join(missing)
        raise SystemExit(
            f"Manjkajo obvezna orodja: {names}\n"
            "Na Arch/CachyOS jih lahko namestis z: sudo pacman -S imagemagick python"
        )


def get_heif_decoders() -> list[str]:
    return [candidate for candidate in ("heif-convert", "ffmpeg") if shutil.which(candidate)]


def gather_images(root: Path, recursive: bool) -> list[Path]:
    results: list[Path] = []
    if recursive:
        for current_root, dirnames, filenames in os.walk(root, topdown=True):
            dirnames[:] = [
                name
                for name in dirnames
                if name not in SKIP_DIR_NAMES and not name.startswith(".")
            ]
            current_path = Path(current_root)
            if current_path.name == "compressed":
                continue
            for filename in filenames:
                path = current_path / filename
                if is_supported_image(path):
                    results.append(path)
    else:
        for path in sorted(root.iterdir()):
            if path.is_file() and is_supported_image(path):
                results.append(path)
    return sorted(results)


def is_supported_image(path: Path) -> bool:
    if path.parent.name == "compressed":
        return False
    if any(part.startswith(".") for part in path.parts[:-1]):
        return False
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def make_output_path(
    source: Path,
    source_root: Path,
    output_root: Path,
    recursive: bool,
    reserved: set[Path],
    output_format: str = "jpg",
) -> Path:
    relative_parent = source.parent.relative_to(source_root) if recursive else Path()
    target_dir = output_root / relative_parent
    target_dir.mkdir(parents=True, exist_ok=True)
    base_name = source.stem
    candidate = target_dir / f"{base_name}.{output_format}"
    counter = 2
    while candidate in reserved or candidate.exists():
        candidate = target_dir / f"{base_name}_{counter}.{output_format}"
        counter += 1
    reserved.add(candidate)
    return candidate


def run_command(args: list[str], error_context: str) -> None:
    completed = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        details = stderr or stdout or "brez dodatnega izpisa"
        raise RuntimeError(f"{error_context}: {details}")


def prepare_input(source: Path, temp_dir: Path) -> Path:
    if source.suffix.lower() not in HEIF_EXTENSIONS:
        return source

    decoders = get_heif_decoders()
    if not decoders:
        raise RuntimeError(
            "Za HEIC/HEIF/AVIF ni na voljo niti 'heif-convert' niti 'ffmpeg'. "
            "Namesti enega od njiju."
        )

    errors: list[str] = []
    for index, decoder in enumerate(decoders, start=1):
        decoded = temp_dir / f"decoded_{index}.png"
        try:
            if decoder == "heif-convert":
                run_command(
                    ["heif-convert", str(source), str(decoded)],
                    f"Napaka pri dekodiranju '{source.name}' z heif-convert",
                )
            else:
                run_command(
                    ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), str(decoded)],
                    f"Napaka pri dekodiranju '{source.name}' z ffmpeg",
                )
            return decoded
        except RuntimeError as exc:
            errors.append(str(exc))

    raise RuntimeError(" | ".join(errors))


def get_dimensions(image_path: Path) -> tuple[int, int]:
    completed = subprocess.run(
        ["identify", "-format", "%w %h", f"{image_path}[0]"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "identify failed"
        raise RuntimeError(f"Napaka pri branju dimenzij: {details}")
    raw_width, raw_height = completed.stdout.strip().split()
    return int(raw_width), int(raw_height)


def encode_candidate(source: Path, destination: Path, width: int, height: int, quality: int, output_format: str) -> int:
    args = [
        "magick",
        f"{source}[0]",
        "-auto-orient",
        "-colorspace",
        "sRGB",
        "-filter",
        "Lanczos",
        "-resize",
        f"{width}x{height}>",
        "-sampling-factor",
        "4:2:0",
        "-strip",
        "-interlace",
        "Plane",
        "-quality",
        str(quality),
        "-define",
        "png:compression-level=9",
        "-define",
        "webp:method=6",
        str(destination),
    ]
    run_command(args, f"Napaka pri ustvarjanju '{destination.name}'")
    return destination.stat().st_size


def find_best_candidate(
    source: Path,
    temp_dir: Path,
    width: int,
    height: int,
    max_bytes: int,
    min_quality: int,
    max_quality: int,
    output_format: str = "jpg",
) -> tuple[Path, int] | tuple[None, None]:
    best_path: Path | None = None
    best_quality: int | None = None
    low = min_quality
    high = max_quality

    while low <= high:
        quality = (low + high) // 2
        candidate_path = temp_dir / f"candidate_q{quality}.{output_format}"
        size_bytes = encode_candidate(source, candidate_path, width, height, quality, output_format)
        if size_bytes <= max_bytes:
            best_path = candidate_path
            best_quality = quality
            low = quality + 1
        else:
            high = quality - 1

    if best_path is None or best_quality is None:
        return None, None

    final_copy = temp_dir / f"best_q{best_quality}.{output_format}"
    shutil.copy2(best_path, final_copy)
    return final_copy, final_copy.stat().st_size


def compress_image(source: Path, destination: Path, max_bytes: int, output_format: str = "jpg") -> int:
    with tempfile.TemporaryDirectory(prefix="compress-images-") as tmp:
        temp_dir = Path(tmp)
        prepared = prepare_input(source, temp_dir)
        original_width, original_height = get_dimensions(prepared)
        width = original_width
        height = original_height

        while True:
            best_path, best_size = find_best_candidate(
                prepared,
                temp_dir,
                width,
                height,
                max_bytes,
                MIN_QUALITY,
                START_QUALITY,
                output_format,
            )
            if best_path is not None and best_size is not None:
                shutil.move(best_path, destination)
                return best_size

            if min(width, height) <= MIN_DIMENSION:
                break

            width = max(MIN_DIMENSION, int(width * RESIZE_FACTOR))
            height = max(MIN_DIMENSION, int(height * RESIZE_FACTOR))

        while True:
            best_path, best_size = find_best_candidate(
                prepared,
                temp_dir,
                width,
                height,
                max_bytes,
                EMERGENCY_MIN_QUALITY,
                START_QUALITY,
                output_format,
            )
            if best_path is not None and best_size is not None:
                shutil.move(best_path, destination)
                return best_size

            if width <= 1 or height <= 1:
                raise RuntimeError("Ciljne velikosti ni bilo mogoce doseci.")

            width = max(1, int(width * RESIZE_FACTOR))
            height = max(1, int(height * RESIZE_FACTOR))


def format_bytes(size: int) -> str:
    sign = "-" if size < 0 else ""
    size = abs(size)
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    if unit == "B":
        return f"{sign}{int(value)} {unit}"
    if value >= 100:
        return f"{sign}{value:.0f} {unit}"
    if value >= 10:
        return f"{sign}{value:.1f} {unit}"
    return f"{sign}{value:.2f} {unit}"


def main() -> int:
    args = parse_args()
    ensure_dependencies()

    if args.max_size_mb is None:
        max_size_mb = prompt_for_size_mb()
    else:
        try:
            max_size_mb = parse_size_mb(args.max_size_mb)
        except ValueError as exc:
            print(f"Napaka: {exc}", file=sys.stderr)
            return 2

    max_bytes = max(1, int(max_size_mb * 1024 * 1024))
    cwd = Path.cwd()
    output_root = cwd / "compressed"
    images = gather_images(cwd, args.recursive)

    print(f"Found {len(images)} images")
    print(f"Target max size: {max_size_mb:.2f} MB | Format: {args.format.upper()}")

    if not images:
        print("\nDone.")
        print("0 converted")
        print("0 failed")
        print("0 skipped")
        print("Original: 0 B")
        print("Compressed: 0 B")
        print("Saved: 0 B")
        return 0

    converted = 0
    failed = 0
    skipped = 0
    total_original = 0
    total_compressed = 0
    reserved_paths: set[Path] = set()

    for index, source in enumerate(images, start=1):
        original_size = source.stat().st_size
        total_original += original_size
        destination = make_output_path(source, cwd, output_root, args.recursive, reserved_paths, args.format)
        try:
            compressed_size = compress_image(source, destination, max_bytes, args.format)
        except Exception as exc:
            failed += 1
            print(f"[{index}/{len(images)}] {source.name} -> FAILED ({exc})")
            continue

        converted += 1
        total_compressed += compressed_size
        print(
            f"[{index}/{len(images)}] {source.name} -> {destination.name} | "
            f"{format_bytes(original_size)} -> {format_bytes(compressed_size)}"
        )

    saved = total_original - total_compressed

    print("\nDone.")
    print(f"{converted} converted")
    print(f"{failed} failed")
    print(f"{skipped} skipped")
    print(f"Original: {format_bytes(total_original)}")
    print(f"Compressed: {format_bytes(total_compressed)}")
    print(f"Saved: {format_bytes(saved)}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

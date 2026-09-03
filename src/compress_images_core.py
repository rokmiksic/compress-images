#!/usr/bin/env python3

import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
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
            "Batch convert images and ensure every output file is at or below "
            "the requested size in MB."
        ),
    )
    parser.add_argument(
        "max_size_mb",
        nargs="?",
        help="Maximum allowed size per image in MB, for example 0.5, 1, 1.5 or 2",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan subdirectories and preserve their structure below 'compressed/'.",
    )
    parser.add_argument(
        "--format",
        choices=("jpg", "webp", "avif", "png"),
        default="jpg",
        help="Output format: jpg, webp, avif or png (default: jpg).",
    )
    return parser.parse_args()


def parse_size_mb(raw: str) -> float:
    value = raw.strip().replace(",", ".")
    try:
        size_mb = float(value)
    except ValueError as exc:
        raise ValueError("Enter a valid decimal number, for example 0.5, 1 or 1.5.") from exc
    if not math.isfinite(size_mb) or size_mb <= 0:
        raise ValueError("Size must be a positive number greater than zero.")
    return size_mb


def prompt_for_size_mb() -> float:
    while True:
        raw = input("Maximum allowed size per image in MB: ").strip()
        try:
            return parse_size_mb(raw)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)


def ensure_dependencies() -> None:
    required = ["python3", "magick", "identify"]
    missing = [name for name in required if shutil.which(name) is None]
    if missing:
        names = ", ".join(missing)
        raise SystemExit(
            f"Required tools are missing: {names}\n"
            "On Arch/CachyOS, install them with: sudo pacman -S imagemagick python"
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
        details = stderr or stdout or "no additional output"
        raise RuntimeError(f"{error_context}: {details}")


def prepare_input(source: Path, temp_dir: Path) -> Path:
    if source.suffix.lower() not in HEIF_EXTENSIONS:
        return source

    decoders = get_heif_decoders()
    if not decoders:
        raise RuntimeError(
            "Neither 'heif-convert' nor 'ffmpeg' is available for HEIC/HEIF/AVIF. "
            "Install one of them."
        )

    errors: list[str] = []
    for index, decoder in enumerate(decoders, start=1):
        decoded = temp_dir / f"decoded_{index}.png"
        try:
            if decoder == "heif-convert":
                run_command(
                    ["heif-convert", str(source), str(decoded)],
                    f"Failed to decode '{source.name}' with heif-convert",
                )
            else:
                run_command(
                    ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), str(decoded)],
                    f"Failed to decode '{source.name}' with ffmpeg",
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
        raise RuntimeError(f"Failed to read image dimensions: {details}")
    raw_width, raw_height = completed.stdout.strip().split()
    return int(raw_width), int(raw_height)


def encode_candidate(
    source: Path,
    destination: Path,
    width: int,
    height: int,
    quality: int,
    output_format: str,
    target_bytes: int | None = None,
) -> int:
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
    ]
    if output_format == "jpg" and target_bytes is not None:
        args.extend(["-define", f"jpeg:extent={target_bytes}B"])
    args.append(str(destination))
    run_command(args, f"Failed to create '{destination.name}'")
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

    # Most images fit at the starting quality; avoid a full binary search in that case.
    initial_path = temp_dir / f"candidate_q{max_quality}.{output_format}"
    initial_size = encode_candidate(source, initial_path, width, height, max_quality, output_format)
    if initial_size <= max_bytes:
        return initial_path, initial_size

    if output_format == "jpg":
        extent_path = temp_dir / "candidate_extent.jpg"
        extent_size = encode_candidate(
            source, extent_path, width, height, max_quality, output_format, max_bytes
        )
        if extent_size <= max_bytes:
            return extent_path, extent_size

    low = min_quality
    high = max_quality - 1

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

    return best_path, best_path.stat().st_size


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
                raise RuntimeError("Could not reach the requested target size.")

            width = max(1, int(width * RESIZE_FACTOR))
            height = max(1, int(height * RESIZE_FACTOR))


def compress_batch(
    images: list[Path],
    source_root: Path,
    output_root: Path,
    recursive: bool,
    max_bytes: int,
    output_format: str,
    on_result=None,
) -> list[tuple[int, Path, Path, int | None, Exception | None]]:
    """Compress a batch with bounded parallelism while reserving names first."""
    reserved_paths: set[Path] = set()
    jobs = [
        (
            index,
            source,
            make_output_path(source, source_root, output_root, recursive, reserved_paths, output_format),
        )
        for index, source in enumerate(images, start=1)
    ]
    worker_count = min(len(jobs), max(1, min(os.cpu_count() or 2, 4)))
    results: list[tuple[int, Path, Path, int | None, Exception | None]] = []
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="compress") as executor:
        futures = {
            executor.submit(compress_image, source, destination, max_bytes, output_format): (index, source, destination)
            for index, source, destination in jobs
        }
        for future in as_completed(futures):
            index, source, destination = futures[future]
            try:
                result = (index, source, destination, future.result(), None)
            except Exception as exc:
                result = (index, source, destination, None, exc)
            results.append(result)
            if on_result is not None:
                on_result(result)
    return sorted(results, key=lambda item: item[0])


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
            print(f"Error: {exc}", file=sys.stderr)
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
    results = compress_batch(images, cwd, output_root, args.recursive, max_bytes, args.format)
    for index, source, destination, compressed_size, error in results:
        original_size = source.stat().st_size
        total_original += original_size
        if error is not None:
            failed += 1
            print(f"[{index}/{len(images)}] {source.name} -> FAILED ({error})")
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

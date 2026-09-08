# compress-images Handoff

This file records the current state for the next agent working on this project.

## Project

- Public repository: https://github.com/rokmiksic/compress-images
- Local project: `/home/rok/Dokumenti/ChatGPT/ta računalnik/compress-images`
- Current user: Slovenian CachyOS/Arch Linux desktop with KDE Plasma and Fish.
- Current latest release work: `v0.2.1`; `master` now also contains post-release fixes through commit `14a045f`.
- License: MIT. The project is intended to remain fully open source and accept contributions.
- CLI language is English-only. The GTK GUI remains multilingual.

## Features

The project provides:

- `compress-images` CLI and `compress-images-gui` GTK4 GUI.
- Exact per-file maximum output size, entered in MB or KB.
- Decimal input with either `.` or `,`, for example `0.5` and `0,5`.
- JPG, WEBP, AVIF and PNG output selection in the GUI/CLI.
- Input support through ImageMagick, libheif/heif-convert and FFmpeg fallbacks for common formats including JPG, JPEG, PNG, WEBP, HEIC, HEIF, AVIF, TIFF and BMP.
- JPEG quality search, a JPEG extent fast path, and progressive resizing when quality reduction alone cannot meet the target.
- Aspect-ratio preservation, EXIF orientation correction and metadata stripping.
- Originals are never modified.
- The GUI must accept files explicitly selected by the user even when they have no filename extension; Dolphin can identify such files as JPEG. Folder scanning still uses supported extensions.
- Collision-safe output names such as `photo.jpg` and `photo_2.jpg`.
- Skips `compressed/` and hidden cache directories.
- Optional recursive processing while preserving the relative directory structure.
- Batch processing with bounded parallelism for faster conversion.
- Summary of converted, failed/skipped files and before/after total sizes.

## GUI settings persistence

Settings are stored at:

`~/.config/compress-images/settings.json`

The stored values include `language`, `unit`, `format`, `recursive` and `limit`. The current test file contained:

```json
{
  "language": "Slovenian",
  "unit": "MB",
  "format": "JPG",
  "recursive": false,
  "limit": "0,5"
}
```

The GUI fix in `src/compress_images_gui.py` is important:

- GTK uses `Gio.ApplicationFlags.NON_UNIQUE` so Plasma does not reuse a stale single-instance process.
- `do_activate()` reloads settings before rebuilding the window.
- Saves use UTF-8, `ensure_ascii=False`, and atomic temporary-file replacement.
- The local launcher uses the installed GUI executable, not the source checkout.
- `build_ui()` calls `refresh_text()` after creating all widgets, so the saved language is applied immediately on startup instead of only after manually changing the language dropdown.

If the user still sees old choices, close the existing GUI window completely and start a fresh instance from Plasma. The current installed executable is `/home/rok/.local/bin/compress-images-gui`.

## Local installation

Installed user files:

- `/home/rok/.local/bin/compress-images`
- `/home/rok/.local/bin/compress-images-gui`
- `/home/rok/.local/bin/compress_images_core.py`
- `/home/rok/.local/bin/compress_images_gui.py`
- `/home/rok/.local/share/applications/compress-images.desktop`
- Icons under `/home/rok/.local/share/icons/hicolor/*/apps/com.github.compress-images.png`

Fish already includes `$HOME/.local/bin` in `/home/rok/.config/fish/config.fish`. The Plasma desktop launcher uses absolute paths because Plasma may not inherit Fish's interactive PATH.

System package dependencies used by the Arch package are `python`, `python-gobject`, `gtk4`, `imagemagick`, `ffmpeg` and `libheif`. Install only missing dependencies after checking with `pacman -Q` or `command -v`.

## Important files

- `src/compress_images_core.py`: shared conversion/compression engine and CLI support.
- `src/compress_images_gui.py`: GTK4 GUI, translations, settings and batch progress.
- `src/compress-images`: CLI wrapper.
- `src/compress-images-gui`: GUI wrapper.
- `packaging/PKGBUILD`: Arch package definition.
- `packaging/.SRCINFO`: generated Arch metadata; regenerate from `packaging/` when package metadata changes.
- `packaging/debian/build-deb.sh`: Debian package builder.
- `packaging/debian/control.in`: Debian package metadata.
- `packaging/compress-images.desktop`: installed system desktop entry.
- `.github/workflows/arch-package.yml`: Arch package build and release asset workflow.
- `.github/workflows/debian-package.yml`: Debian package build and release asset workflow.
- `assets/icons/`: included MIT-licensed application icon in multiple sizes.

## Packaging and publication

GitHub Actions build Arch `.pkg.tar.zst` and Debian `.deb` release assets. Verify both workflow runs and both assets after every tagged release. The Node.js 20 deprecation annotation from GitHub Actions is a warning about action runtime migration, not the package failure itself; update action versions only if the workflow actually breaks.

AUR account registration was temporarily paused by AUR anti-abuse measures. Do not script retries. When registration is available, create/use the AUR account, configure SSH, regenerate `.SRCINFO`, and publish a separate AUR package repository. Until then, GitHub release assets and direct package builds are the supported distribution paths. Omarchy can use the GitHub package/release or a future AUR package; AUR is not a prerequisite for running the program.

## Verification already performed

- The installed GUI launched successfully with `timeout`; the timeout exit code `124` meant the GUI stayed running, not that it crashed.
- Startup log was empty/no GTK startup errors.
- The settings file was read with `language: Slovenian` and the other saved values.
- JPEG files without extensions were reproduced from `/home/rok/Prejemi`; after the GUI selection fix, three such files compressed successfully below `512 KiB` without changing the originals.
- The saved-language startup fix was tested with `~/.config/compress-images/settings.json` set to `Slovenian`; the GUI started without errors and the fix was pushed to GitHub `master` as `14a045f`.
- A previously running old GUI process was intentionally not killed because it was processing user images. Never interrupt an active compression job or modify originals.
- The project has been committed and pushed through the `v0.2.1` release work. Re-check `git status`, `git log`, workflow status and release assets before further changes.

## Safe next steps

1. Let any active compression process finish before testing or killing processes.
2. Check `git -C /home/rok/Dokumenti/ChatGPT/ta računalnik/compress-images status --short` before editing.
3. Reproduce GUI persistence by changing language/options, closing the GUI fully, and reopening it from Plasma.
4. Test originals in a temporary copy only; verify every output is at or below the requested size and that source files have unchanged hashes.
5. For release changes, update version metadata consistently, regenerate `.SRCINFO`, run package builds, push the tag, and verify both GitHub assets.

The current `v0.2.1` release assets were built before the latest startup-language fix. Create a new version/tag and rebuild both Arch and Debian assets before claiming the packaged release includes `14a045f`.

Do not delete or overwrite the user's original images. Do not reset or discard unrelated working-tree changes.

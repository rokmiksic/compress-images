# User guide

## GUI

Run `compress-images-gui` from the application menu or terminal. Choose either a complete folder or individual image files. Select the maximum size, choose `MB` or `KB`, select an output format, and press **Start compression**.

The folder option can include subfolders. Results are written to a `compressed/` directory below the selected folder. When individual files are selected, the common parent directory is used and its relative folder structure is preserved.

The application remembers the language, size value, `MB`/`KB` unit, output format, and subfolder setting in `~/.config/compress-images/settings.json`. This is a small user-only JSON file and can be deleted to restore defaults.

Each launcher activation starts an instance that reloads this file, so an older GUI process cannot keep stale language or option values.

Batch jobs use bounded parallel workers. JPG output first checks a high-quality candidate and uses ImageMagick's target-size encoder when appropriate; the exact final size is still verified and the existing resize fallback remains active.

Supported output formats are `JPG`, `WEBP`, `AVIF`, and `PNG`. The encoder searches for the highest suitable quality first and then reduces dimensions while preserving aspect ratio. EXIF orientation is applied and metadata is stripped. Existing output files are never overwritten.

## CLI

```sh
compress-images                 # asks for size in MB and writes JPG
compress-images 1                # 1 MB per image
compress-images 500 --format jpg --recursive
compress-images 0.5 --format webp
```

The CLI size argument is in MB. The GUI additionally supports KB directly. Both decimal separators `0.5` and `0,5` are accepted by the GUI and CLI.

## Safety

Original files are read-only inputs. The program skips hidden directories, `compressed/`, unsupported extensions, and already-existing destination names. A failed image is reported and does not stop the remaining batch.

# User guide

## GUI

Run `compress-images-gui` from the application menu or terminal. Choose or drag in a complete folder, individual image files, or a ZIP archive. Select the maximum size, choose `MB` or `KB`, optionally set the maximum long-edge resolution in pixels, select an output format, and press **Start compression**.

You can drag items directly from Dolphin anywhere onto the application window. The entire window content is a drop target and accepts images, folders, and ZIP files. A dropped folder is processed like a folder selected with **Choose folder**; dropped files and ZIP archives are processed like **Choose images or ZIP**.

The folder option can include subfolders. Results are written to a `compressed/` directory below the selected folder. When individual files are selected, the common parent directory is used and its relative folder structure is preserved.

When a ZIP archive is selected, the archive is read-only. Its images are extracted to a temporary directory, converted with the same size limit, and written below `compressed/<archive-name>/` with the internal folder structure preserved. A ready-to-share `compressed/<archive-name>-compressed.zip` is created as well. Unsafe absolute paths, parent-directory traversal and symbolic links inside the input archive are rejected.

The application remembers the language, size value, `MB`/`KB` unit, output format, maximum resolution, and subfolder setting in `~/.config/compress-images/settings.json`. This is a small user-only JSON file and can be deleted to restore defaults.

Each launcher activation starts an instance that reloads this file, so an older GUI process cannot keep stale language or option values.

Batch jobs use bounded parallel workers. JPG output first checks a high-quality candidate and uses ImageMagick's target-size encoder when appropriate; the exact final size is still verified and the existing resize fallback remains active.

Supported output formats are `JPG`, `WEBP`, `AVIF`, and `PNG`. The encoder searches for the highest suitable quality first and then reduces dimensions while preserving aspect ratio. A blank maximum-resolution field enables automatic resolution reduction when the target would otherwise require excessive quality loss. EXIF orientation is applied, embedded sRGB ICC profiles are preserved, and disposable metadata is stripped when no color profile needs to be retained. Existing output files are never overwritten.

## Windows portable bundle

Download `compress-images-windows-x64.zip` from a GitHub Release and extract it. Start `CompressImagesGUI.cmd` for the GUI or run `CompressImagesCLI.cmd 1 --max-dimension 2400` from a terminal. The bundle contains its own Python, GTK4/PyGObject, ImageMagick, FFmpeg and libheif runtime. Windows settings are stored in `%APPDATA%\\compress-images`.

## CLI

```sh
compress-images                 # asks for size in MB and writes JPG
compress-images 1                # 1 MB per image
compress-images 500 --format jpg --recursive
compress-images 0.5 --format webp
compress-images 1 --max-dimension 2400
```

The CLI size argument is in MB. The GUI additionally supports KB directly. Both decimal separators `0.5` and `0,5` are accepted by the GUI and CLI.

`--max-dimension` limits the width or height of the output in pixels and preserves the aspect ratio. For example, `--max-dimension 2400` limits the long edge to 2400 pixels. The CLI also automatically reduces resolution for severe size reductions before using very low quality.

## Safety

Original files are read-only inputs. The program skips hidden directories, `compressed/`, unsupported extensions, and already-existing destination names. A failed image is reported and does not stop the remaining batch.

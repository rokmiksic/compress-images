# AUR release checklist

1. Create a public GitHub repository named `compress-images` and copy this directory into it.
2. The package source already points to `rokmiksic/compress-images`.
3. Commit and create a release tag matching `pkgver`, for example `v0.1.0`.
4. Build locally with `makepkg -si` and test both `compress-images` and `compress-images-gui`.
5. Create the AUR repository `compress-images` and push `PKGBUILD` plus the generated `.SRCINFO`.

For a release archive instead of a git source, use a versioned GitHub tarball in `source`, run `updpkgsums`, and commit the resulting checksum. Do not leave `sha256sums=('SKIP')` in a production AUR package unless the source is intentionally a git checkout.

The package installs the GUI launcher at `/usr/bin/compress-images-gui`, the CLI at `/usr/bin/compress-images`, shared Python modules under `/usr/lib/compress-images`, and the desktop entry under `/usr/share/applications/`.

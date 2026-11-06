# AUR release checklist

1. Create a public GitHub repository named `compress-images` and copy this directory into it.
2. The package source points to `rokmiksic/compress-images`; keep the source tag aligned with the current release, currently `v0.2.4`.
3. Commit and create a release tag matching `pkgver`, currently `v0.2.4`.
4. Build locally with `makepkg -si` and test both `compress-images` and `compress-images-gui`.
5. Create the AUR repository `compress-images` and push `PKGBUILD` plus the generated `.SRCINFO`.

For a release archive instead of a git source, use a versioned GitHub tarball in `source`, run `updpkgsums`, and commit the resulting checksum. Do not leave `sha256sums=('SKIP')` in a production AUR package unless the source is intentionally a git checkout.

The package installs the GUI launcher at `/usr/bin/compress-images-gui`, the CLI at `/usr/bin/compress-images`, shared Python modules under `/usr/lib/compress-images`, and the desktop entry under `/usr/share/applications/`.

## Other Linux distributions

GitHub Releases also provide a Debian/Ubuntu `.deb` package. Fedora and openSUSE would use an RPM package, while Flatpak publication requires a separate Flathub review and a sandbox-specific dependency setup because the application calls ImageMagick, FFmpeg and libheif.

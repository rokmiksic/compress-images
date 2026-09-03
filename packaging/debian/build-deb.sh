#!/usr/bin/env bash
set -euo pipefail

version="${1:?Usage: build-deb.sh VERSION}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
package_root="$root/packaging/debian/pkg"
rm -rf "$package_root"
install -d "$package_root/DEBIAN" "$package_root/usr/bin" "$package_root/usr/lib/compress-images" "$package_root/usr/share/applications"
sed "s/^Version: VERSION$/Version: $version/" "$root/packaging/debian/control.in" > "$package_root/DEBIAN/control"
install -m755 "$root/src/compress-images" "$package_root/usr/bin/compress-images"
install -m755 "$root/src/compress-images-gui" "$package_root/usr/bin/compress-images-gui"
install -m755 "$root/src/compress_images_core.py" "$package_root/usr/lib/compress-images/compress_images_core.py"
install -m755 "$root/src/compress_images_gui.py" "$package_root/usr/lib/compress-images/compress_images_gui.py"
install -m644 "$root/packaging/compress-images.desktop" "$package_root/usr/share/applications/compress-images.desktop"
for size in 16 32 48 64 128 256 512; do
  install -Dm644 "$root/assets/icons/compress-images-${size}.png" \
    "$package_root/usr/share/icons/hicolor/${size}x${size}/apps/com.github.compress-images.png"
done
dpkg-deb --build --root-owner-group "$package_root" "$root/packaging/compress-images_${version}_all.deb"

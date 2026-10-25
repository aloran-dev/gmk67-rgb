#!/bin/sh
# Construye dist/gmk67-rgb_<versión>_all.deb con dpkg-deb (sin debhelper).
set -e
cd "$(dirname "$0")/../.."
VERSION=${1:?uso: build-deb.sh <versión>}
ROOT=$(mktemp -d)
trap 'rm -rf "$ROOT"' EXIT
chmod 755 "$ROOT"

make install DESTDIR="$ROOT" PREFIX=/usr UDEVDIR=/usr/lib/udev/rules.d
install -Dm644 LICENSE "$ROOT/usr/share/doc/gmk67-rgb/copyright"

mkdir -p "$ROOT/DEBIAN"
SIZE=$(du -sk --exclude=DEBIAN "$ROOT" | cut -f1)
sed -e "s/@VERSION@/$VERSION/" -e "s/@SIZE@/$SIZE/" packaging/deb/control > "$ROOT/DEBIAN/control"
install -m755 packaging/deb/postinst "$ROOT/DEBIAN/postinst"
install -m755 packaging/deb/postinst "$ROOT/DEBIAN/postrm"

mkdir -p dist
dpkg-deb --root-owner-group --build "$ROOT" "dist/gmk67-rgb_${VERSION}_all.deb"

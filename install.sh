#!/bin/sh
# Instala la regla udev (pide sudo) y el lanzador en el menú de aplicaciones.
set -e
cd "$(dirname "$(realpath "$0")")"

sudo install -m 644 70-gmk67.rules /etc/udev/rules.d/70-gmk67.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=hidraw

chmod +x gmk67-rgb
mkdir -p ~/.local/bin ~/.local/share/applications
ln -sf "$PWD/gmk67-rgb" ~/.local/bin/gmk67-rgb
cat > ~/.local/share/applications/dev.aloran.Gmk67Rgb.desktop <<EOF
[Desktop Entry]
Name=GMK67
Comment=Cambiar las luces del teclado GMK67
Exec=$HOME/.local/bin/gmk67-rgb
Icon=input-keyboard
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;
EOF
echo "Listo. Abre «GMK67» desde el menú o ejecuta gmk67-rgb"

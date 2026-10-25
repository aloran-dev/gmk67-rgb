#!/bin/sh
# Instalación desde el código fuente para el usuario actual: la app en ~/.local
# y la regla udev en el sistema (pide sudo). Para desinstalar: ./install.sh --uninstall
set -e
cd "$(dirname "$(realpath "$0")")"

if [ "$1" = "--uninstall" ]; then
    make uninstall PREFIX="$HOME/.local" UDEVDIR=
    sudo rm -f /etc/udev/rules.d/70-gmk67.rules
    exit
fi

sudo install -m 644 70-gmk67.rules /etc/udev/rules.d/70-gmk67.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=hidraw

make install PREFIX="$HOME/.local" UDEVDIR=
# Lanzador de versiones anteriores (antes del cambio de ID de la app)
rm -f ~/.local/share/applications/dev.aloran.Gmk67Rgb.desktop
echo "Listo. Abre «GMK67» desde el menú o ejecuta gmk67-rgb"

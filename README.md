# gmk67-rgb

Control de las luces RGB del teclado **Zuoya GMK67 (v1)** en Linux, con una app GTK4 + libadwaita.

*Linux RGB control for the Zuoya GMK67 (v1, `05ac:024f`, "hfd.cn USB DEVICE") keyboard. GTK4/libadwaita app plus a small Python module documenting the protocol.*

## Qué hace

- 19 efectos más "Apagado": estático, respiración, ola, flujo, ondas, etc.
- Color, colores aleatorios, brillo, velocidad y dirección.
- Historial con los últimos 8 colores aplicados.
- Corrección de color para los LEDs del teclado: sin ella, el naranja se ve amarillo y los verdes azulados se ven azules.
- Al abrirse, lee el efecto que tiene puesto el teclado.

## Compatibilidad

Solo el **GMK67 v1** conectado **por cable USB**. Se identifica así:

```
$ lsusb
... ID 05ac:024f Apple, Inc. Aluminium Keyboard (ANSI)   ← ID prestado por el firmware
$ cat /sys/class/hidraw/hidraw*/device/uevent | grep hfd
HID_NAME=hfd.cn USB DEVICE
```

El GMK67 **v2** (`36b0:3068`) usa QMK/VIA y no necesita esto: funciona con [VIA](https://usevia.app).

## Instalación

Descarga el paquete de tu distribución desde [Releases](https://github.com/aloran-dev/gmk67-rgb/releases):

| Distribución | Instalar |
|---|---|
| Ubuntu 24.04+, Debian 13+, Mint, Pop!_OS | `sudo apt install ./gmk67-rgb_*_all.deb` |
| Fedora 39+ | `sudo dnf install ./gmk67-rgb-*.noarch.rpm` |
| Cualquiera con Flatpak | `flatpak install --user gmk67-rgb-*.flatpak` |

El `.deb` y el `.rpm` instalan una regla udev que da acceso al teclado al usuario de la sesión. Un Flatpak no puede instalar reglas en el sistema, así que con Flatpak hay que añadirla una vez a mano. La app muestra los comandos la primera vez que no puede acceder al teclado.

### Desde el código fuente

Necesitas Python 3, PyGObject, GTK 4.12+ y libadwaita 1.4+ (en Ubuntu/Debian: `python3-gi gir1.2-gtk-4.0 gir1.2-adw-1`).

```sh
git clone https://github.com/aloran-dev/gmk67-rgb.git
cd gmk67-rgb
./install.sh            # app en ~/.local + regla udev (pide sudo)
./install.sh --uninstall
```

## Protocolo

Se obtuvo analizando el driver oficial de Windows. Son *feature reports* HID de 64 bytes, sin report ID, en la interfaz 0 del teclado. Para poner un efecto se envía:

| Paquete | Significado |
|---|---|
| `04 18` | activar el efecto por software |
| `04 13 00 00 00 00 00 00 01` | se va a escribir 1 página |
| `[modo, R, G, B, 0, 0, 0, 0, aleatorio, brillo+1, velocidad+1, dirección, 0, 0, AA, 55]` | la página del efecto |
| `04 02` | fin de la escritura |
| `04 F0` | aplicar |

Cada comando se confirma con un GET_FEATURE que devuelve `04 <cmd> 00 01`. Los modos van de `0x01` a `0x13` y `0x00` apaga las luces. El brillo y la velocidad van de 0 a 15. Los detalles están en [`gmk67.py`](gmk67.py).

Se parece al protocolo del Keychron K3 V2 que soporta OpenRGB, pero la secuencia de OpenRGB (`04 19` + 18 páginas) este teclado la acepta y la ignora.

Los cambios hechos con las teclas Fn no se reflejan en el efecto guardado por software.

También se puede usar sin la interfaz:

```python
import gmk67
with gmk67.Keyboard() as kb:
    kb.set_effect(gmk67.Effect(0x07, color=(255, 128, 0), speed=12))  # respiración naranja
```

## Licencia

[GPL-3.0](LICENSE)

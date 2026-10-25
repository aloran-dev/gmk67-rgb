"""Protocolo RGB del Zuoya GMK67 (v1, firmware hfd.cn HFD801KJC, 05ac:024f).

Sacado del driver oficial (DeviceDriver.exe, FUN_0041db20): feature reports
de 64 bytes sin report ID en la interfaz 0. Para poner un efecto manda:

    04 18                       activar el efecto por software
    04 13 .. .. .. .. .. .. 01  se va a escribir 1 página
    [página del efecto]
    04 02                       fin de la escritura
    04 F0                       aplicar

Cada comando se confirma con un GET_FEATURE que devuelve "04 <cmd> 00 01".
"""

import fcntl
import glob
import os
import time
from dataclasses import dataclass, field

VID, PID = 0x05AC, 0x024F
PACKET_LEN = 64
HEADER = 0x04
CHECK_L, CHECK_H = 0xAA, 0x55
DELAY = 0.015  # el driver espera 15 ms entre paquetes

CMD_COMM_END = 0x02
CMD_READ_EFFECT = 0x12
CMD_WRITE_EFFECT = 0x13
CMD_SOFTWARE_EFFECT = 0x18
CMD_EFFECT_START = 0xF0

# Los LEDs no son lineales como una pantalla: sin gamma el naranja ff8000 se ve
# amarillo, y el azul domina tanto que el menta 1deeb2 se ve azul. Se corrige al
# enviar y se deshace al leer. Valores ajustados a ojo sobre el teclado.
GAMMA = 2.2
GAIN = (0.97, 1.0, 0.33)  # R, G, B después de la gamma

MAX_LEVEL = 0x0F  # brillo y velocidad van de 0 a 15; en la página van +1

DIR_NONE, DIR_LR, DIR_UD = 0, 1, 2

# (valor, nombre, admite color, admite velocidad, tipo de dirección)
# Valores de la tabla de modos del driver (1033.lan, ids 200-219).
MODES = [
    (0x01, "Estático", True, False, DIR_NONE),
    (0x02, "Encender al pulsar", True, True, DIR_NONE),
    (0x03, "Apagar al pulsar", True, True, DIR_NONE),
    (0x04, "Destellos", True, True, DIR_NONE),
    (0x05, "Lluvia", True, True, DIR_NONE),
    (0x06, "Colores aleatorios", False, True, DIR_NONE),
    (0x07, "Respiración", True, True, DIR_NONE),
    (0x08, "Ciclo de espectro", False, True, DIR_NONE),
    (0x09, "Hacia fuera", True, True, DIR_NONE),
    (0x0A, "Desplazamiento", True, True, DIR_UD),
    (0x0B, "Ola", True, True, DIR_LR),
    (0x0C, "Giro", True, True, DIR_NONE),
    (0x0D, "Explosión", True, True, DIR_NONE),
    (0x0E, "Lanzamiento", True, True, DIR_NONE),
    (0x0F, "Ondas", True, True, DIR_NONE),
    (0x10, "Flujo", True, True, DIR_LR),
    (0x11, "Pulsos", True, True, DIR_NONE),
    (0x12, "Inclinado", True, True, DIR_NONE),
    (0x13, "Lanzadera", True, True, DIR_LR),
    (0x00, "Apagado", False, False, DIR_NONE),
]

# Direcciones en bruto: 0 izq→der, 1 der→izq, 2 abajo→arriba, 3 arriba→abajo
DIRECTIONS = {
    DIR_LR: [(0, "Izquierda → derecha"), (1, "Derecha → izquierda")],
    DIR_UD: [(2, "Abajo → arriba"), (3, "Arriba → abajo")],
}


def to_led(color):
    linear = [(c / 255) ** GAMMA for c in color]
    balanced = [v * k for v, k in zip(linear, GAIN)]
    # Reescala para que el canal más fuerte conserve su intensidad (el azul puro no se apaga)
    scale = max(linear) / max(balanced) if max(balanced) else 0
    return tuple(round(255 * v * scale) for v in balanced)


def from_led(color):
    balanced = [c / 255 for c in color]
    linear = [v / k for v, k in zip(balanced, GAIN)]
    scale = max(balanced) / max(linear) if max(linear) else 0
    return tuple(min(round(255 * (v * scale) ** (1 / GAMMA)), 255) for v in linear)


def _ioc(direction, nr, size):
    return (direction << 30) | (size << 16) | (ord("H") << 8) | nr


def HIDIOCSFEATURE(size):
    return _ioc(3, 0x06, size)


def HIDIOCGFEATURE(size):
    return _ioc(3, 0x07, size)


@dataclass
class Effect:
    value: int
    color: tuple = (255, 255, 255)
    random: bool = False
    brightness: int = MAX_LEVEL
    speed: int = 10
    direction: int = 0

    def page(self):
        b = bytearray(PACKET_LEN)
        b[0] = self.value
        b[1:4] = bytes(to_led(self.color))
        b[8] = int(self.random)
        b[9] = self.brightness + 1
        b[10] = self.speed + 1
        b[11] = self.direction
        b[14], b[15] = CHECK_L, CHECK_H
        return bytes(b)


@dataclass
class Profile:
    """Ajustes de cada efecto, para recordarlos al cambiar de modo en la app."""
    effects: dict = field(default_factory=lambda: {m[0]: Effect(m[0]) for m in MODES})
    active: int = 0x01


class DeviceNotFound(Exception):
    pass


class ProtocolError(Exception):
    pass


def find_hidraw():
    """Devuelve /dev/hidrawN de la interfaz 0 del GMK67."""
    for sysdir in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            with open(os.path.join(sysdir, "device/uevent")) as f:
                uevent = dict(l.strip().split("=", 1) for l in f if "=" in l)
            with open(os.path.join(sysdir, "device/report_descriptor"), "rb") as f:
                desc = f.read()
        except OSError:
            continue
        if uevent.get("HID_ID", "").upper() != f"0003:{VID:08X}:{PID:08X}":
            continue
        # La interfaz de control tiene un feature report de 64 bytes (95 40 75 08 b1 02)
        # y es la del teclado (05 01 09 06); un teclado Apple real no lo tiene.
        if desc.startswith(b"\x05\x01\x09\x06") and b"\x95\x40\x75\x08\xb1\x02" in desc:
            return "/dev/" + os.path.basename(sysdir)
    raise DeviceNotFound("No se encontró el GMK67 conectado por cable USB")


class Keyboard:
    def __init__(self, path=None):
        self.path = path or find_hidraw()
        self.fd = os.open(self.path, os.O_RDWR)

    def close(self):
        os.close(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def send(self, data):
        buf = bytearray(PACKET_LEN + 1)  # byte 0 = report ID 0
        buf[1:1 + len(data)] = data
        time.sleep(DELAY)
        fcntl.ioctl(self.fd, HIDIOCSFEATURE(len(buf)), buf)

    def read(self):
        buf = bytearray(PACKET_LEN + 1)
        time.sleep(DELAY)
        fcntl.ioctl(self.fd, HIDIOCGFEATURE(len(buf)), buf, True)
        return bytes(buf[1:])

    def command(self, cmd, pages=0):
        pkt = bytearray(PACKET_LEN)
        pkt[0], pkt[1], pkt[8] = HEADER, cmd, pages
        self.send(pkt)
        reply = self.read()
        if reply[:2] != bytes([HEADER, cmd]) or reply[3] != 0x01:
            raise ProtocolError(f"El teclado no confirmó el comando {cmd:02x}: {reply[:9].hex(' ')}")

    def set_effect(self, effect: Effect):
        self.command(CMD_SOFTWARE_EFFECT)
        self.command(CMD_WRITE_EFFECT, 1)
        self.send(effect.page())
        self.command(CMD_COMM_END)
        self.command(CMD_EFFECT_START)

    def read_effect(self):
        """Efecto guardado por software (no refleja los cambios hechos con Fn)."""
        pkt = bytearray(PACKET_LEN)
        pkt[0], pkt[1], pkt[8] = HEADER, CMD_READ_EFFECT, 1
        self.send(pkt)
        # Normalmente responde con la página directamente, pero a veces antes llega la confirmación
        page = self.read()
        if page[:4] == bytes([HEADER, CMD_READ_EFFECT, 0, 1]):
            page = self.read()
        self.command(CMD_COMM_END)
        return Effect(value=page[0], color=from_led(page[1:4]), random=bool(page[8]),
                      brightness=max(page[9] - 1, 0), speed=max(page[10] - 1, 0),
                      direction=page[11])


if __name__ == "__main__":
    with Keyboard() as kb:
        print(kb.path, kb.read_effect())

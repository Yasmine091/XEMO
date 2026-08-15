"""Small, optional LD06/LD19 dToF packet reader.

The scanner is deliberately disabled by default: existing Xemo builds have no
LiDAR wired, and importing this module must not claim GPIOs or change boot.
Set ``ENABLED = True`` and choose UART/pins for a build that has one.  The
driver only parses packets; SLAM/map building belongs on the phone or laptop.
"""

import machine

ENABLED = False
UART_ID = 1
UART_BAUD = 230400
UART_TX = 4
UART_RX = 5


class LDScan:
    def __init__(self, uart):
        self.uart = uart
        self.buf = bytearray()
        self.latest = None

    @staticmethod
    def _crc(data):
        crc = 0
        for value in data:
            crc ^= value
            for _ in range(8):
                crc = ((crc << 1) ^ 0x4D) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
        return crc

    @staticmethod
    def _u16(data, at):
        return data[at] | (data[at + 1] << 8)

    def poll(self):
        n = self.uart.any()
        if n:
            chunk = self.uart.read(n)
            if chunk:
                self.buf.extend(chunk)
        while len(self.buf) >= 47:
            if self.buf[0] != 0x54:
                del self.buf[0]
                continue
            if self.buf[1] != 0x2C:
                del self.buf[:2]
                continue
            packet = bytes(self.buf[:47])
            del self.buf[:47]
            if self._crc(packet[:-1]) != packet[-1]:
                continue
            start = self._u16(packet, 4) / 100.0
            end = self._u16(packet, 42) / 100.0
            span = (end - start) % 360.0
            points = []
            for i in range(12):
                at = 6 + i * 3
                angle = (start + span * i / 11.0) % 360.0
                distance = self._u16(packet, at) / 1000.0
                quality = packet[at + 2]
                if distance > 0:
                    points.append([round(angle, 2), round(distance, 3), quality])
            self.latest = {"start": round(start, 2), "end": round(end, 2),
                           "points": points}
        return self.latest


def open_scanner():
    if not ENABLED:
        return None
    uart = machine.UART(UART_ID, baudrate=UART_BAUD, tx=machine.Pin(UART_TX),
                        rx=machine.Pin(UART_RX), timeout=0, timeout_char=1)
    return LDScan(uart)

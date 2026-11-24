"""Leitura e gravacao dos scripts do motor NeXAS (Script.pac) e dos textos do Config.pac."""
import re
import struct

from .accents import from_game_bytes, to_game_bytes

NEVER_TRANSLATE = re.compile(r"\.\w{2,4}$|^SE\d+$|^#BG|^EF_|^\d+$|[_\\/]", re.IGNORECASE)
TEXT_RE = re.compile(rb"(?<=[\x00\xff])[A-Za-z][\x20-\x7e]*?(?=\x00)")
DAT_FILES = ("button.dat", "event.dat", "eventtype.dat", "configstring.dat")


def split_script(data: bytes):
    """Script .bin: u32 n, n*8 bytes de codigo, u32 quantidade de textos, textos com \\0 no fim, resto."""
    n = struct.unpack_from("<I", data, 0)[0]
    end = 4 + n * 8
    count = struct.unpack_from("<I", data, end)[0]
    strings, p = [], end + 4
    for _ in range(count):
        z = data.index(b"\0", p)
        strings.append(data[p:z])
        p = z + 1
    return data[:end], strings, data[p:]


def join_script(code: bytes, strings: list, tail: bytes) -> bytes:
    return code + struct.pack("<I", len(strings)) + b"".join(s + b"\0" for s in strings) + tail


def is_dialogue(s: str) -> bool:
    return s.startswith("@v") or (s.startswith(" ") and bool(s.strip()))


def is_ignored(s: str) -> bool:
    """Vazio, nome de arquivo, numero ou identificador interno: nunca traduzido."""
    return not s.strip() or (not is_dialogue(s) and bool(NEVER_TRANSLATE.search(s.strip())))


def dat_fit(text: bytes, size: int) -> bytes:
    if len(text) > size:
        cut = text[:size + 1].rsplit(b" ", 1)[0] if b" " in text[:size + 1] else text[:size]
        text = cut[:size]
    return text.ljust(size, b" ")


def dat_replace(data: bytes, new: dict) -> bytes:
    out = bytearray(data)
    for offset, text in new.items():
        size = data.index(b"\0", offset) - offset
        out[offset:offset + size] = dat_fit(text, size)
    return bytes(out)


def decode_game(b: bytes) -> str:
    return from_game_bytes(b)


def encode_game(s: str) -> bytes:
    return to_game_bytes(s)

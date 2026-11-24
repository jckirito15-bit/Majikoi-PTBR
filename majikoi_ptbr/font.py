"""Fonte com acentos para o Majikoi: instala 'TraduVN Maru' so para o usuario e troca a fonte no Config.dat."""
import ctypes
import os
import struct
import zlib
from pathlib import Path

from .accents import build_font

GAME_FONT_FILE = "MotoyaLMaruM.ttf"
GAME_FAMILY = b"MotoyaLMaruM"
FAMILY = "TraduVN Maru"  # mesmo tamanho do nome original: troca byte a byte no Config.dat
REG_KEY = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"
assert len(FAMILY) == len(GAME_FAMILY)


def config_dat() -> Path:
    return Path.home() / "Documents" / "Minato Soft" / "Majikoi" / "Save" / "Config.dat"


def user_fonts_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Microsoft" / "Windows" / "Fonts"


def install_font(game_dir: Path) -> Path:
    """Gera a fonte a partir da fonte do proprio jogo e registra para o usuario (sem administrador)."""
    import winreg
    dst = user_fonts_dir() / "TraduVNMaru.ttf"
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp")
    build_font(str(Path(game_dir) / GAME_FONT_FILE), str(tmp), FAMILY)
    gdi = ctypes.windll.gdi32
    for _ in range(50):  # o Windows pode ter carregado a fonte varias vezes (login + cada instalacao)
        if not dst.exists() or not gdi.RemoveFontResourceW(str(dst)):
            break
    os.replace(tmp, dst)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY) as key:
        winreg.SetValueEx(key, f"{FAMILY} (TrueType)", 0, winreg.REG_SZ, str(dst))
    gdi.AddFontResourceW(str(dst))
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001D, 0, 0, 0x0002, 1000, None)  # WM_FONTCHANGE
    return dst


def switch_config_font(path: Path, to_accents: bool) -> bool:
    """Troca o nome da fonte salvo nas opcoes do jogo. Devolve False se o jogo ainda nao criou o arquivo."""
    if not path.is_file():
        return False
    raw = path.read_bytes()
    # u32 versao, depois blocos (u32 tamanho, u32 tamanho zlib, dados): a fonte esta no primeiro bloco
    head, _, packed_size = struct.unpack_from("<3I", raw)
    data, rest = zlib.decompress(raw[12:12 + packed_size]), raw[12 + packed_size:]
    old, new = (GAME_FAMILY, FAMILY.encode()) if to_accents else (FAMILY.encode(), GAME_FAMILY)
    if old not in data:
        return new in data
    data = data.replace(old, new)
    packed = zlib.compress(data, 9)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(struct.pack("<3I", head, len(data), len(packed)) + packed + rest)
    os.replace(tmp, path)
    return True

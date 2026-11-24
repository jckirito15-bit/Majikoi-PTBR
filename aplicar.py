"""Majikoi! Love Me Seriously! - Traducao PT-BR (por Professor Dazai).

Uso:
    python aplicar.py "<pasta do jogo>"              instala a traducao (faz backup dos originais)
    python aplicar.py "<pasta do jogo>" --restaurar  volta ao jogo original
    python aplicar.py "<pasta do jogo>" --sem-fonte  instala so os textos (sem a fonte com acentos)

A pasta do jogo e a que tem Majikoi.exe e Script.pac (Steam: botao direito no jogo > Gerenciar > Ver arquivos locais).
Os originais ficam em <pasta do jogo>\\PTBR_backup. Feche o jogo antes.
"""
import hashlib
import json
import struct
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from majikoi_ptbr.nexas import TEXT_RE, dat_replace, encode_game, join_script, split_script  # noqa: E402
from majikoi_ptbr.pac import read_pac, replace_in_place, write_pac  # noqa: E402

BACKUP = "PTBR_backup"
FILES = ("Script.pac", "Config.pac")
LOGO_PAC, LOGO_NAME = "Visual.pac", b"start_logo.bmp"  # tela de abertura: ganha a logo do Professor Dazai


def sha1(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def jogo_aberto() -> bool:
    if os.name != "nt" or os.environ.get("PTBR_SEM_CHECAGEM"):
        return False
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Majikoi.exe"], capture_output=True).stdout or b""
    return b"Majikoi.exe" in out


def aplicar_script(src: Path, dst: Path, trad: dict) -> int:
    method, entries = read_pac(src)
    feitos = 0
    for e in entries:
        t = trad["script"].get(e.name.decode("cp932"))
        if not t:
            continue
        code, strings, tail = split_script(e.data)
        if len(strings) != t["n"]:
            sys.exit(f"ERRO: {e.name.decode('cp932')} tem {len(strings)} textos, a traducao espera {t['n']}. "
                     "O jogo nao e a versao 'Steam' original que a traducao foi feita.")
        for i, txt in t["textos"].items():
            strings[int(i)] = encode_game(txt)
            feitos += 1
        for i, hx in t.get("bytes", {}).items():
            strings[int(i)] = bytes.fromhex(hx)
            feitos += 1
        e.data = join_script(code, strings, tail)
    write_pac(dst, method, entries)
    return feitos


def aplicar_config(src: Path, dst: Path, trad: dict) -> tuple:
    shutil.copy2(src, dst)
    changes, feitos, pulados = {}, 0, 0
    for e in read_pac(dst)[1]:
        itens = trad["config"].get(e.name.decode("cp932"))
        if not itens:
            continue
        new = {}
        for off, txt in itens.items():
            m = TEXT_RE.match(e.data, int(off))
            if m is None:  # o original nao tem texto nesse ponto: nao mexe
                pulados += 1
                continue
            new[int(off)] = encode_game(txt)
            feitos += 1
        if new:
            changes[e.name] = dat_replace(e.data, new)
    if changes:
        replace_in_place(dst, changes)
    return feitos, pulados


def _tail(path: Path):
    """(onde comeca o indice, bytes do indice + u32 final) de um .pac."""
    with open(path, "rb") as f:
        f.seek(-4, 2)
        size = struct.unpack("<I", f.read(4))[0]
        start = f.seek(-4 - size, 2)
        return start, f.read()


def logo_instalar(game: Path, bk: Path) -> None:
    pac = game / LOGO_PAC
    bmp = HERE / "assets" / "start_logo.bmp"
    if not pac.is_file() or not bmp.is_file():
        return
    info = bk / (LOGO_PAC + ".info")
    if info.is_file():  # reaplicacao: volta ao indice original antes
        logo_restaurar(game, bk)
    start, tail = _tail(pac)
    (bk / (LOGO_PAC + ".tail")).write_bytes(tail)
    info.write_text(str(start))
    replace_in_place(pac, {LOGO_NAME: bmp.read_bytes()})
    print("Logo do Professor Dazai colocada na abertura.")


def logo_restaurar(game: Path, bk: Path) -> None:
    info, tail = bk / (LOGO_PAC + ".info"), bk / (LOGO_PAC + ".tail")
    if not (info.is_file() and tail.is_file()):
        return
    with open(game / LOGO_PAC, "r+b") as f:
        f.seek(int(info.read_text()))
        f.truncate()
        f.write(tail.read_bytes())
    info.unlink()
    tail.unlink()


def instalar(game: Path, com_fonte: bool) -> None:
    trad = json.loads((HERE / "traducao" / "majikoi-ptbr.json").read_text(encoding="utf-8"))
    bk = game / BACKUP
    bk.mkdir(exist_ok=True)
    for n in FILES:
        if (game / n).is_file() and not (bk / n).is_file():
            shutil.copy2(game / n, bk / n)  # primeiro uso: o que esta no jogo agora e o original
    t, c = game / "Script.pac.tmp", game / "Config.pac.tmp"
    n_script = aplicar_script(bk / "Script.pac", t, trad)
    n_cfg, pulados = (0, 0)
    if (bk / "Config.pac").is_file():
        n_cfg, pulados = aplicar_config(bk / "Config.pac", c, trad)
    os.replace(t, game / "Script.pac")
    if c.is_file():
        os.replace(c, game / "Config.pac")
    if "--sem-logo" not in sys.argv:
        logo_instalar(game, bk)
    print(f"Textos do roteiro gravados: {n_script}. Textos de menu: {n_cfg} (pulados: {pulados}).")
    if com_fonte:
        try:
            from majikoi_ptbr import font
            ttf = game / font.GAME_FONT_FILE
            if ttf.is_file():
                font.install_font(game)
                font.switch_config_font(font.config_dat(), to_accents=True)
                print("Fonte com acentos instalada (TraduVN Maru, so para o seu usuario).")
            else:
                print("Aviso: MotoyaLMaruM.ttf nao esta na pasta; sem a fonte os acentos saem errados.")
        except Exception as ex:  # sem fontTools/Windows: os textos ficam, os acentos nao
            print("Aviso: nao consegui instalar a fonte com acentos:", ex, "(pip install fonttools)")
    print("Pronto. Abra o jogo.")


def restaurar(game: Path) -> None:
    bk = game / BACKUP
    if not bk.is_dir():
        sys.exit("Nao ha backup: o jogo ainda esta original.")
    for n in FILES:
        if (bk / n).is_file():
            shutil.copy2(bk / n, game / n)
    logo_restaurar(game, bk)
    try:
        from majikoi_ptbr import font
        font.switch_config_font(font.config_dat(), to_accents=False)
    except Exception:
        pass
    print("Jogo original restaurado.")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    game = Path(args[0])
    if not (game / "Script.pac").is_file() or not (game / "Majikoi.exe").is_file():
        sys.exit("Pasta errada: nao achei Majikoi.exe e Script.pac nela.")
    if jogo_aberto():
        sys.exit("Feche o jogo antes.")
    if "--restaurar" in sys.argv:
        restaurar(game)
    else:
        instalar(game, "--sem-fonte" not in sys.argv)


if __name__ == "__main__":
    main()

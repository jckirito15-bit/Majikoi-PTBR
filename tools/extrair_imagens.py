"""Ferramenta do autor: extrai as imagens traduzidas (menus, botoes, datas, telas de batalha) de um Majikoi JA traduzido.

As imagens traduzidas sao as que a tradutora regravou no fim do System.pac, em ordem alfabetica.
Uso: python tools/extrair_imagens.py "<pasta do jogo traduzido>"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from majikoi_ptbr import pac  # noqa: E402


def main(game: Path) -> None:
    path = game / "System.pac"
    with open(path, "rb") as fh:
        _, count, _ = pac.HEADER.unpack(fh.read(pac.HEADER.size))
        idx, _ = pac._read_index(fh, count)
    ent = sorted((pac._entry_fields(idx, i)[1][0], pac._entry_fields(idx, i)[0]) for i in range(count))
    j = len(ent) - 1
    while j > 0 and ent[j - 1][1] < ent[j][1]:
        j -= 1
    names = {n for _, n in ent[j:]}
    data = pac.read_entries(path, names)
    out = Path(__file__).resolve().parents[1] / "imagens" / "System"
    out.mkdir(parents=True, exist_ok=True)
    for n, d in data.items():
        (out / n.decode("cp932")).write_bytes(d)
    print(len(data), "imagens ->", out)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

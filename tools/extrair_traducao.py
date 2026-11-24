"""Ferramenta do autor: extrai a traducao PT-BR de um Majikoi JA traduzido para traducao/majikoi-ptbr.json.

Uso: python tools/extrair_traducao.py "<pasta do jogo traduzido>"
(quem so quer instalar a traducao NAO precisa disto: use aplicar.py)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from majikoi_ptbr.nexas import (DAT_FILES, TEXT_RE, decode_game, encode_game, is_ignored,
                                split_script)
from majikoi_ptbr.pac import read_pac


def main(game: Path) -> None:
    out = {"formato": 1, "jogo": "Majikoi! Love Me Seriously! (Steam, motor NeXAS)", "script": {}, "config": {}}
    total = bad = 0
    for e in read_pac(game / "Script.pac")[1]:
        name = e.name.decode("cp932")
        if not name.startswith(("act_", "system")):
            continue
        _, strings, _ = split_script(e.data)
        textos, raw = {}, {}
        for i, s in enumerate(strings):
            if is_ignored(s.decode("cp932", errors="replace")):
                continue
            t = decode_game(s)
            if encode_game(t) == s:
                textos[str(i)] = t
            else:  # nao volta byte a byte pelo texto: guarda os bytes exatos
                raw[str(i)] = s.hex()
                bad += 1
            total += 1
        out["script"][name] = {"n": len(strings), "textos": textos}
        if raw:
            out["script"][name]["bytes"] = raw
    for e in read_pac(game / "Config.pac")[1]:
        name = e.name.decode("cp932")
        if name.lower() not in DAT_FILES:
            continue
        itens = {}
        for m in TEXT_RE.finditer(e.data):
            t = m.group().decode("ascii").rstrip(" ")
            if " " in t.strip():
                itens[str(m.start())] = t
        out["config"][name] = itens
    dst = Path(__file__).resolve().parents[1] / "traducao" / "majikoi-ptbr.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"scripts: {len(out['script'])}, textos: {total} (guardados em bytes: {bad}), config: "
          f"{sum(len(v) for v in out['config'].values())} -> {dst}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

"""Acentos no jogo sem Unicode: cada letra acentuada vira um byte 0xA1-0xDF (1 byte so em Shift-JIS; 0xE0+ o
jogo leria como inicio de caractere de 2 bytes). O jogo cria a fonte com charset ANSI, entao o Windows le esse
byte como cp1252 (0xC1 -> U+00C1 'Á', 0xA2 -> U+00A2 '¢'). Uma copia da fonte do jogo desenha nesses codigos a
letra acentuada, montada com a letra base + o acento da propria fonte (mesmo estilo do resto do texto)."""
import unicodedata

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

ASCII_MAP = str.maketrans({"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "…": "...",
                           "—": "-", "–": "-", "«": '"', "»": '"', " ": " "})

ACCENTED = "áéíóúâêôãõçàüÁÉÍÓÚÂÊÔÃÕÇÀÜ"
# maiusculas: o proprio byte cp1252 (0xC0-0xDC). Minusculas (0xE0+ em cp1252) vao para bytes livres 0xA2-0xB9,
# fora dos que o texto em ingles ja usa como simbolos (0xA1, 0xA5, 0xA9-0xAC, 0xAE-0xB0, 0xB2, 0xD7).
GAME_BYTE = {c: b for c, b in zip("áéíóúâêôãõçàü", bytes.fromhex("a2 a3 a4 a6 a7 a8 b3 b4 b5 b6 b7 b8 b9"))}
GAME_BYTE.update({c: c.encode("cp1252")[0] for c in "ÁÉÍÓÚÂÊÔÃÕÇÀÜ"})
FROM_BYTE = {b: c for c, b in GAME_BYTE.items()}
# codigo Unicode que o Windows busca na fonte para cada letra (byte lido como cp1252)
SLOT = {c: ord(bytes([b]).decode("cp1252")) for c, b in GAME_BYTE.items()}
# letra acentuada -> (letra base, nome do acento)
PARTS = {}
for base, marks in {"a": "áâãàÁÂÃÀ", "e": "éêÉÊ", "i": "íÍ", "o": "óôõÓÔÕ", "u": "úüÚÜ", "c": "çÇ"}.items():
    for ch in marks:
        PARTS[ch] = (base.upper() if ch.isupper() else base,
                     {"á": "acute", "é": "acute", "í": "acute", "ó": "acute", "ú": "acute", "â": "circ",
                      "ê": "circ", "ô": "circ", "ã": "tilde", "õ": "tilde", "ç": "cedilla", "à": "grave",
                      "ü": "dieresis"}[ch.lower()])


def to_game_bytes(text: str) -> bytes:
    """Texto final para o jogo: acentos -> bytes da fonte, o resto em ASCII puro."""
    text = unicodedata.normalize("NFC", text.translate(ASCII_MAP))
    out = bytearray()
    for c in text:
        if c in GAME_BYTE:
            out.append(GAME_BYTE[c])
        else:
            out += (unicodedata.normalize("NFKD", c) if ord(c) > 127 else c).encode("ascii", "ignore")
    return bytes(out)


def from_game_bytes(data: bytes) -> str:
    return "".join(FROM_BYTE.get(b, chr(b)) for b in data)


def _outline(font: TTFont, glyph: str) -> DecomposingRecordingPen:
    pen = DecomposingRecordingPen(font.getGlyphSet())
    font.getGlyphSet()[glyph].draw(pen)
    return pen


def _bounds(font: TTFont, glyph: str):
    from fontTools.pens.boundsPen import BoundsPen
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[glyph].draw(pen)
    return pen.bounds


def _drop_contours_above(ops: list, limit: float) -> list:
    out, contour = [], []
    for op in ops:
        contour.append(op)
        if op[0] in ("closePath", "endPath"):
            ys = [pt[1] for _, pts in contour for pt in pts]
            if not ys or min(ys) < limit:
                out += contour
            contour = []
    return out + contour


def _mark(font: TTFont, cmap: dict, kind: str):
    """Glifo-fonte e escala de cada acento (os da fonte japonesa sao grandes, de largura inteira)."""
    return {"acute": (cmap[0xB4], 0.55), "grave": (cmap[0x60], 0.8), "circ": (cmap[0x5E], 0.8),
            "tilde": (cmap[0x7E], 0.8), "dieresis": (cmap[0xA8], 0.55), "cedilla": (cmap[0x2C], 0.7)}[kind]


def build_font(src: str, dst: str, family: str):
    font = TTFont(src)
    cmap = dict(font.getBestCmap())  # copia: os slots cp1252 (´ ¨) mudam no loop, os acentos-fonte nao
    glyf, hmtx = font["glyf"], font["hmtx"]
    vmtx = font["vmtx"] if "vmtx" in font else None
    order = font.getGlyphOrder()
    x_height = _bounds(font, cmap[ord("x")])[3]
    cap_height = _bounds(font, cmap[ord("H")])[3]
    for ch, (base, kind) in PARTS.items():
        base_glyph = cmap[ord(base)]
        width = hmtx[base_glyph][0]
        bx0, _, bx1, _ = _bounds(font, base_glyph)
        mark_glyph, scale = _mark(font, cmap, kind)
        mx0, my0, mx1, my1 = _bounds(font, mark_glyph)
        top = cap_height if base.isupper() else x_height
        if base.isupper():
            scale *= 0.85
        pen = TTGlyphPen(font.getGlyphSet())
        base_pen = _outline(font, base_glyph)
        if base == "i":  # tira o pingo do i para o acento ficar no lugar dele
            base_pen.value = _drop_contours_above(base_pen.value, x_height)
        base_pen.replay(pen)
        center = (bx0 + bx1) / 2
        dx = center - (mx0 + mx1) / 2 * scale
        if kind == "cedilla":  # virgula embaixo da letra
            dy = -my1 * scale + 30
        else:
            dy = top + 60 - my0 * scale
        _outline(font, mark_glyph).replay(TransformPen(pen, (scale, 0, 0, scale, dx, dy)))
        target = f"traduvn_{ord(ch):04x}"  # glifo novo: os codigos cp1252 nao tem desenho proprio que preste
        order.append(target)
        glyf[target] = pen.glyph()
        glyf[target].recalcBounds(glyf)
        hmtx[target] = (width, glyf[target].xMin)
        if vmtx is not None:
            vmtx[target] = vmtx[base_glyph]
        for table in font["cmap"].tables:
            if table.isUnicode():
                table.cmap[SLOT[ch]] = target
    font.setGlyphOrder(order)
    glyf.glyphOrder = order
    for record in font["name"].names:
        if record.nameID in (1, 3, 4, 6, 16):
            text = family if record.nameID != 6 else family.replace(" ", "")
            record.string = text
    font.save(dst)

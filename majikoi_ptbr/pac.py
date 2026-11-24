"""Leitura e gravacao dos arquivos .pac do motor NeXAS.

Formato: cabecalho "PAC\\0" + u32 quantidade + u32 metodo; dados (zlib, ou crus quando
o tamanho comprimido == tamanho real); indice no fim, codificado com Huffman e XOR 0xFF,
com entradas de 76 bytes (nome 64 + offset, tamanho real, tamanho comprimido);
os ultimos 4 bytes guardam o tamanho do indice codificado.
"""
import heapq
import itertools
import struct
import zlib
from dataclasses import dataclass

HEADER = struct.Struct("<4sII")
ENTRY_SIZE = 76
NAME_SIZE = 64


@dataclass
class PacEntry:
    name: bytes
    data: bytes


class _BitReader:
    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def get(self, n: int) -> int:
        v = 0
        for _ in range(n):
            v = (v << 1) | ((self.data[self.pos >> 3] >> (7 - (self.pos & 7))) & 1)
            self.pos += 1
        return v


def huff_decode(data: bytes, out_len: int) -> bytes:
    br = _BitReader(data)
    lhs, rhs = {}, {}
    next_node = 256

    def tree() -> int:
        nonlocal next_node
        if br.get(1):
            v = next_node
            next_node += 1
            lhs[v] = tree()
            rhs[v] = tree()
            return v
        return br.get(8)

    root = tree()
    out = bytearray()
    while len(out) < out_len:
        v = root
        while v >= 256:
            v = rhs[v] if br.get(1) else lhs[v]
        out.append(v)
    return bytes(out)


def huff_encode(data: bytes) -> bytes:
    freq = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    counter = itertools.count()
    heap = [(f, next(counter), b) for b, f in freq.items()]
    if len(heap) == 1:
        heap.append((0, next(counter), (heap[0][2] + 1) & 0xFF))
    heapq.heapify(heap)
    while len(heap) > 1:
        a, b = heapq.heappop(heap), heapq.heappop(heap)
        heapq.heappush(heap, (a[0] + b[0], next(counter), (a[2], b[2])))

    bits, codes = [], {}

    def walk(node, code):
        if isinstance(node, tuple):
            bits.append(1)
            walk(node[0], code + [0])
            walk(node[1], code + [1])
        else:
            bits.append(0)
            bits.extend((node >> (7 - i)) & 1 for i in range(8))
            codes[node] = code

    walk(heap[0][2], [])
    for b in data:
        bits.extend(codes[b])
    out = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        if bit:
            out[i >> 3] |= 0x80 >> (i & 7)
    return bytes(out)


def _xor(data: bytes) -> bytes:
    return bytes(b ^ 0xFF for b in data)


def _read_index(f, count: int) -> tuple[bytearray, int]:
    """Devolve (indice decodificado, posicao onde o indice comeca)."""
    f.seek(-4, 2)
    size = struct.unpack("<I", f.read(4))[0]
    start = f.seek(-4 - size, 2)
    return bytearray(huff_decode(_xor(f.read(size)), count * ENTRY_SIZE)), start


def _entry_fields(idx, i):
    e = idx[i * ENTRY_SIZE:(i + 1) * ENTRY_SIZE]
    return bytes(e[:NAME_SIZE]).split(b"\0")[0], struct.unpack_from("<III", e, NAME_SIZE)


def _write_index(f, idx: bytes) -> None:
    packed = _xor(huff_encode(bytes(idx)))
    f.write(packed)
    f.write(struct.pack("<I", len(packed)))


def read_pac(path) -> tuple[int, list[PacEntry]]:
    with open(path, "rb") as f:
        magic, count, method = HEADER.unpack(f.read(HEADER.size))
        if magic != b"PAC\0":
            raise ValueError(f"{path}: nao e um arquivo PAC")
        idx, _ = _read_index(f, count)
        entries = []
        for i in range(count):
            name, (off, usize, psize) = _entry_fields(idx, i)
            f.seek(off)
            blob = f.read(psize)
            entries.append(PacEntry(name, zlib.decompress(blob) if psize != usize else blob))
    return method, entries


def _index_entry(name: bytes, off: int, usize: int, psize: int) -> bytes:
    return name.ljust(NAME_SIZE, b"\0") + struct.pack("<III", off, usize, psize)


def write_pac(path, method: int, entries: list[PacEntry]) -> None:
    with open(path, "wb") as f:
        f.write(HEADER.pack(b"PAC\0", len(entries), method))
        idx = bytearray()
        for e in entries:
            comp = zlib.compress(e.data, 9)
            idx += _index_entry(e.name, f.tell(), len(e.data), len(comp))
            f.write(comp)
        _write_index(f, idx)


def replace_in_place(path, replacements: dict[bytes, bytes]) -> None:
    """Acrescenta os dados novos no fim e regrava o indice, sem reescrever o resto."""
    with open(path, "r+b") as f:
        _, count, _ = HEADER.unpack(f.read(HEADER.size))
        idx, index_start = _read_index(f, count)
        names = {_entry_fields(idx, i)[0]: i for i in range(count)}
        missing = set(replacements) - set(names)
        if missing:
            raise KeyError(f"arquivos nao encontrados no PAC: {sorted(missing)}")
        f.seek(index_start)
        f.truncate()
        for name, data in replacements.items():
            comp = zlib.compress(data, 9)
            i = names[name]
            struct.pack_into("<III", idx, i * ENTRY_SIZE + NAME_SIZE, f.tell(), len(data), len(comp))
            f.write(comp)
        _write_index(f, idx)


def list_names(path) -> list[bytes]:
    with open(path, "rb") as f:
        _, count, _ = HEADER.unpack(f.read(HEADER.size))
        idx, _ = _read_index(f, count)
        return [_entry_fields(idx, i)[0] for i in range(count)]


def read_entries(path, names: set[bytes], index_tail: bytes | None = None) -> dict[bytes, bytes]:
    """Le so os arquivos pedidos, sem carregar o PAC inteiro.

    index_tail: final original do arquivo (indice + u32), para ler a versao original
    de um PAC alterado so com acrescimos.
    """
    out = {}
    with open(path, "rb") as f:
        _, count, _ = HEADER.unpack(f.read(HEADER.size))
        if index_tail is None:
            idx, _ = _read_index(f, count)
        else:
            idx = bytearray(huff_decode(_xor(index_tail[:-4]), count * ENTRY_SIZE))
        for i in range(count):
            name, (off, usize, psize) = _entry_fields(idx, i)
            if name in names:
                f.seek(off)
                blob = f.read(psize)
                out[name] = zlib.decompress(blob) if psize != usize else blob
    return out

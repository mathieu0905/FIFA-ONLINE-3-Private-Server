"""Replace one existing BIG member without invalidating physical directory order."""
from pathlib import Path
import struct
import bigdir


def replace_member(path, name, payload, usize, align=128):
    path = Path(path)
    old = path.read_bytes()
    table = bytearray(bigdir.table(path))
    records = list(bigdir._walk(table))
    entries = [r[1:] for r in records]
    assert all(a[1] + a[2] <= b[1] for a, b in zip(entries, entries[1:])), 'Source directory is unordered or overlapping'
    index = next(i for i, entry in enumerate(entries) if entry[0] == name)
    _, offset, size, _ = entries[index]
    after = entries[index + 1][1] if index + 1 < len(entries) else len(old)
    new_after = (offset + len(payload) + align - 1) // align * align
    shift = new_after - after
    result = bytearray(old[:offset]) + payload + bytes(new_after - offset - len(payload)) + old[after:]
    for i, (pos, member, off, count, unpacked) in enumerate(records):
        if i == index:
            struct.pack_into('>III', table, pos, bigdir.enc(offset), bigdir.enc(len(payload)), bigdir.enc(usize))
            key = len(payload) & 255
            for j, ch in enumerate(member.encode('latin1')):
                value = ch ^ key
                table[pos + 16 + j] = ((value << 4) | (value >> 4)) & 255
                key = ((value or len(payload) & 255) - 0x66) & 255
        elif i > index:
            struct.pack_into('>I', table, pos, bigdir.enc(off + shift))
    struct.pack_into('<I', table, 4, len(result))
    result[:len(table)] = table
    # Validate a private sibling before replacing even the staged artifact.
    temporary = path.with_suffix(path.suffix + '.ordered-next')
    try:
        temporary.write_bytes(result)
        actual = bigdir.entries(temporary)
        assert [e[0] for e in actual] == [e[0] for e in entries]
        assert all(a[1] + a[2] <= b[1] for a, b in zip(actual, actual[1:]))
        for before, after_entry in zip(entries, actual):
            n, o, s, u = before
            _, no, ns, nu = after_entry
            if n == name:
                assert result[no:no + ns] == payload and nu == usize
            else:
                assert result[no:no + ns] == old[o:o + s] and (ns, nu) == (s, u), n
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {name: (offset, len(payload), usize)}

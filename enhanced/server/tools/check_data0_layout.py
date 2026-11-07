"""Read-only layout gate for this FO3 build's BIg4 data_0.big.

This is a structural gate, never proof that the native game will start.  It does
not import production tools (and therefore cannot create their __pycache__).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

DB_MEMBER = 'data/db2/fifadb.db.db2'


def decode(value: int) -> int:
    swapped = ((value << 4) & 0xF0F0F0F0) | ((value >> 4) & 0x0F0F0F0F)
    return ~(swapped ^ 0x2938FA72) & 0xFFFFFFFF


def read_directory(path: Path):
    size = path.stat().st_size
    with path.open('rb') as source:
        head = source.read(17)
        if len(head) != 17 or head[:4] != b'BIg4':
            raise ValueError('Not a complete BIg4 header')
        declared = struct.unpack_from('<I', head, 4)[0]
        count, header_size = (decode(v) for v in struct.unpack_from('>II', head, 8))
        if not 17 <= header_size <= size:
            raise ValueError('Directory size is outside file bounds')
        if count > (header_size - 17) // 17:
            raise ValueError('Directory count cannot fit the header')
        source.seek(0)
        table = source.read(header_size)
    entries = []
    position = 17
    for index in range(count):
        if position + 17 > header_size:
            raise ValueError(f'Entry {index} header is truncated')
        offset, packed, unpacked, length = (decode(v) for v in struct.unpack_from('>IIII', table, position))
        end = position + 17 + length
        if end > header_size:
            raise ValueError(f'Entry {index} name is outside directory bounds')
        key, name = packed & 255, bytearray()
        for byte in table[position + 16:position + 16 + length]:
            swapped = ((byte << 4) | (byte >> 4)) & 255
            name.append(swapped ^ key)
            key = ((swapped or packed & 255) - 0x66) & 255
        entries.append(dict(index=index, name=name.decode('latin1'), offset=offset,
                            packed_size=packed, unpacked_size=unpacked,
                            terminator=table[end - 1]))
        position = end
    return dict(file_size=size, declared_size=declared, header_size=header_size,
                decoded_flag=head[16], count=count, entries=entries)


def file_hash(path: Path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def range_hash(source, offset, size):
    source.seek(offset)
    digest = hashlib.sha256()
    remaining = size
    while remaining:
        block = source.read(min(remaining, 1024 * 1024))
        if not block:
            raise ValueError('Member payload ended before declared size')
        digest.update(block)
        remaining -= len(block)
    return digest.hexdigest()


def inspect(path: Path, baseline: Path | None = None,
            changed_members: set[str] | None = None, expected_count: int | None = None):
    path = path.resolve()
    report = dict(path=str(path), status='FAIL', native_runtime_verified=False, violations=[])
    errors = report['violations']
    try:
        directory = read_directory(path)
        entries = directory['entries']
        report.update(sha256=file_hash(path), file_bytes=directory['file_size'],
                      header_bytes=directory['header_size'], directory_entries=len(entries))
        if directory['declared_size'] != directory['file_size']:
            errors.append(dict(code='archive_size', expected=directory['file_size'], actual=directory['declared_size']))
        if directory['decoded_flag'] != 0:
            errors.append(dict(code='disk_decoded_flag', actual=directory['decoded_flag']))
        if expected_count is not None and len(entries) != expected_count:
            errors.append(dict(code='entry_count', expected=expected_count, actual=len(entries)))
        names = [entry['name'] for entry in entries]
        if len(set(names)) != len(names):
            errors.append(dict(code='duplicate_member_name'))
        for entry in entries:
            if entry['terminator'] != 0:
                errors.append(dict(code='name_terminator', index=entry['index']))
            if entry['offset'] < directory['header_size'] or entry['offset'] + entry['packed_size'] > directory['file_size']:
                errors.append(dict(code='member_bounds', index=entry['index'], member=entry['name']))
        for previous, current in zip(entries, entries[1:]):
            if current['offset'] < previous['offset']:
                errors.append(dict(code='directory_offset_order', before=previous['name'], after=current['name'],
                                   before_offset=previous['offset'], after_offset=current['offset']))
        occupied = sorted((entry for entry in entries if entry['packed_size']), key=lambda entry: entry['offset'])
        for previous, current in zip(occupied, occupied[1:]):
            if previous['offset'] + previous['packed_size'] > current['offset']:
                errors.append(dict(code='payload_overlap', before=previous['name'], after=current['name']))
        if baseline is not None:
            original = read_directory(baseline)
            allowed = changed_members if changed_members is not None else {DB_MEMBER}
            original_entries = original['entries']
            if [entry['name'] for entry in original_entries] != names:
                errors.append(dict(code='baseline_member_order_or_count'))
            else:
                compared = 0
                with baseline.open('rb') as old, path.open('rb') as new:
                    for source_entry, target_entry in zip(original_entries, entries):
                        if target_entry['name'] in allowed:
                            continue
                        compared += 1
                        same_metadata = all(source_entry[key] == target_entry[key] for key in ('packed_size', 'unpacked_size'))
                        same_bytes = (range_hash(old, source_entry['offset'], source_entry['packed_size']) ==
                                      range_hash(new, target_entry['offset'], target_entry['packed_size']))
                        if not same_metadata or not same_bytes:
                            errors.append(dict(code='unexpected_payload_change', member=target_entry['name']))
                report['unchanged_payloads_compared'] = compared
                report['allowed_changed_members'] = sorted(allowed)
        report['status'] = 'FAIL' if errors else 'PASS'
    except (OSError, ValueError, struct.error) as error:
        errors.append(dict(code='parse_or_io_error', detail=str(error)))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', nargs='?', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--expected-count', type=int, default=271, help='654420 data_0 has 271 directory entries')
    parser.add_argument('--changed-member', action='append', dest='changed_members')
    parser.add_argument('--known-regression', nargs=3, type=Path, metavar=('ORIGINAL', 'APPEND_BAD', 'ORDERED'))
    arguments = parser.parse_args()
    if arguments.known_regression:
        original, bad, ordered = arguments.known_regression
        reports = [inspect(original, expected_count=arguments.expected_count),
                   inspect(bad, expected_count=arguments.expected_count),
                   inspect(ordered, baseline=original, expected_count=arguments.expected_count)]
        passed = (reports[0]['status'] == 'PASS' and reports[1]['status'] == 'FAIL'
                  and any(error['code'] == 'directory_offset_order' for error in reports[1]['violations'])
                  and reports[2]['status'] == 'PASS')
        result = dict(status='PASS' if passed else 'FAIL',
                      contract='original PASS; append bad rejected for offset order; ordered PASS and preserves non-DB payloads',
                      native_runtime_verified=False, cases=reports)
    else:
        if arguments.archive is None:
            parser.error('Provide an archive or --known-regression ORIGINAL APPEND_BAD ORDERED')
        result = inspect(arguments.archive, arguments.baseline,
                         set(arguments.changed_members) if arguments.changed_members else None,
                         arguments.expected_count)
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Small synthetic probes from the independent literature-100 boundary audit."""
import hashlib
import io
import json
import math
import random
import struct
import zipfile
import zlib

import numpy as np
import pytest

from hyunoptic.review import export
from hyunoptic.review.validation import evaluate_budget


def _package(payloads, method):
    manifest = dict(schema=export.SCHEMA, files=[dict(name=name, byte_size=len(data),
        sha256=hashlib.sha256(data).hexdigest()) for name, data in sorted(payloads.items())])
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=method) as archive:
        for name, data in dict(payloads, **{'manifest.json': json.dumps(manifest).encode()}).items():
            archive.writestr(name, data)
    return stream.getvalue()


def _concealed_payload_zip(method, declared_size=1):
    """Keep the approved prefix hash/CRC but conceal 1 MiB behind its claimed size."""
    payloads = {name: b'x' for name in export.PAYLOADS}
    manifest = dict(schema=export.SCHEMA, files=[dict(name=name, byte_size=len(data),
        sha256=hashlib.sha256(data).hexdigest()) for name, data in sorted(payloads.items())])
    payloads['manifest.json'] = json.dumps(manifest).encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=method) as archive:
        for name, data in payloads.items():
            archive.writestr(name, data + b'a' * (1024 * 1024) if name == 'cases.csv' else data)
    data = bytearray(stream.getvalue())
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        target = archive.getinfo('cases.csv')
        central_offset = archive.start_dir
    # Patch only metadata, never the compressed payload or the approved manifest.
    struct.pack_into('<I', data, target.header_offset + 14, zlib.crc32(b'x'))
    struct.pack_into('<I', data, target.header_offset + 22, declared_size)
    while data[central_offset:central_offset + 4] == b'PK\x01\x02':
        name_size, extra_size, comment_size = struct.unpack_from('<HHH', data, central_offset + 28)
        name = data[central_offset + 46:central_offset + 46 + name_size].decode()
        if name == 'cases.csv':
            struct.pack_into('<I', data, central_offset + 16, zlib.crc32(b'x'))
            struct.pack_into('<I', data, central_offset + 24, declared_size)
            break
        central_offset += 46 + name_size + extra_size + comment_size
    else:
        raise AssertionError('Fixture lacks cases.csv central record')
    return data


@pytest.mark.parametrize('method', [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA])
def test_verifier_rejects_payloads_exceeding_actual_member_bound(tmp_path, monkeypatch, method):
    package = tmp_path / 'concealed.zip'
    package.write_bytes(_concealed_payload_zip(method))
    monkeypatch.setattr(export, 'MAX_MEMBER_BYTES', 64 * 1024)
    monkeypatch.setattr(export, 'MAX_TOTAL_BYTES', 128 * 1024)
    # Observe actual allocation rather than accepting a declared-size-only test.
    observed = []
    if method == zipfile.ZIP_STORED:
        original = zipfile.ZipExtFile._read2
        def read2(self, size):
            value = original(self, size)
            observed.append(len(value))
            return value
        monkeypatch.setattr(zipfile.ZipExtFile, '_read2', read2)
    else:
        if method == zipfile.ZIP_LZMA:
            original = zipfile.LZMADecompressor.decompress
            def decompress(self, value):
                result = original(self, value)
                observed.append(len(result))
                return result
            monkeypatch.setattr(zipfile.LZMADecompressor, 'decompress', decompress)
        else:
            original_factory = zipfile._get_decompressor
            def factory(kind):
                delegate = original_factory(kind)
                class Observed:
                    def decompress(self, value, *args):
                        result = delegate.decompress(value, *args)
                        observed.append(len(result))
                        return result
                    def __getattr__(self, name):
                        return getattr(delegate, name)
                return Observed()
            monkeypatch.setattr(zipfile, '_get_decompressor', factory)
    try:
        result = export.verify_export(package)
    except ValueError:
        return
    pytest.fail(f'Accepted concealed 1 MiB member under 64 KiB cap: {result}; '
                f'largest actual read/decompression={max(observed)} bytes')


@pytest.mark.parametrize('fraction,expected', [(.07, 7), (.14, 14), (.28, 28)])
def test_review_budget_does_not_round_exact_decimal_percent_up(fraction, expected):
    result = evaluate_budget([False] * 100, review_fraction=fraction)
    assert result['cases_reviewed'] == expected


def test_recovery_never_quarantines_inputs_in_predictions_named_workspace(tmp_path):
    from PIL import Image
    from hyunoptic.review.store import ReviewStore
    stream = io.BytesIO()
    Image.new('RGB', (8, 8)).save(stream, format='PNG')
    store = ReviewStore(tmp_path / 'predictions' / 'workspace' / 'review')
    models = [dict(folder=str(i), identity=str(i), run_id=str(i), weights_sha256=str(i))
              for i in range(2)]
    sid = store.create_session([('source.png', stream.getvalue())], models)
    before = store.cases(sid)[0]
    store.claim(before['id'])
    store.recover(sid)
    assert before['input_path'].is_file(), 'Recovery moved the retained source input into quarantine'
    assert store.cases(sid)[0]['status'] == 'pending'


@pytest.mark.parametrize('method', [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_verifier_accepts_exact_member_cap_with_incompressible_content(tmp_path, monkeypatch, method):
    cap = 64 * 1024
    payloads = {name: b'x' for name in export.PAYLOADS}
    payloads['cases.csv'] = random.Random(42).randbytes(cap)
    package = tmp_path / 'near-cap.zip'
    package.write_bytes(_package(payloads, method))
    monkeypatch.setattr(export, 'MAX_MEMBER_BYTES', cap)
    monkeypatch.setattr(export, 'MAX_TOTAL_BYTES', cap * 2)
    assert export.verify_export(package)['valid']


def test_compressed_member_limit_is_checked_before_opening_member(tmp_path, monkeypatch):
    package = tmp_path / 'large-compressed.zip'
    package.write_bytes(_concealed_payload_zip(zipfile.ZIP_STORED))
    monkeypatch.setattr(export, 'MAX_MEMBER_BYTES', 64 * 1024)
    original = zipfile.ZipFile.open
    def opened(self, member, *args, **kwargs):
        assert getattr(member, 'filename', member) != 'cases.csv', 'Oversized raw input was opened'
        return original(self, member, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, 'open', opened)
    with pytest.raises(ValueError, match='Compressed ZIP member'):
        export.verify_export(package)


def test_archive_size_is_checked_before_central_directory_parsing(tmp_path, monkeypatch):
    package = tmp_path / 'large-container.zip'
    package.write_bytes(b'x' * 33)
    monkeypatch.setattr(export, 'MAX_TOTAL_BYTES', 32)
    monkeypatch.setattr(export, 'ZIP_CONTAINER_OVERHEAD_BYTES', 0)
    monkeypatch.setattr(zipfile, 'ZipFile', lambda *a, **k: pytest.fail('Parsed oversized container'))
    with pytest.raises(ValueError, match='archive exceeds'):
        export.verify_export(package)


def test_central_directory_size_is_checked_before_parser_allocation(tmp_path, monkeypatch):
    payloads = {name: b'x' for name in export.PAYLOADS}
    data = bytearray(_package(payloads, zipfile.ZIP_DEFLATED))
    end = data.rfind(b'PK\x05\x06')
    struct.pack_into('<I', data, end + 12, 2 * 1024 * 1024)
    package = tmp_path / 'large-directory.zip'
    package.write_bytes(data)
    monkeypatch.setattr(zipfile, 'ZipFile', lambda *a, **k: pytest.fail('Allocated oversized directory'))
    with pytest.raises(ValueError, match='central directory exceeds'):
        export.verify_export(package)


def test_raw_stream_shorter_than_declared_is_rejected(tmp_path):
    package = tmp_path / 'short-stream.zip'
    package.write_bytes(_concealed_payload_zip(zipfile.ZIP_DEFLATED, declared_size=2 * 1024 * 1024))
    with pytest.raises(ValueError, match='length or stream-end mismatch'):
        export.verify_export(package)


def test_zip64_cannot_override_preflight_directory_bound(tmp_path, monkeypatch):
    payloads = {name: b'x' for name in export.PAYLOADS}
    data = _package(payloads, zipfile.ZIP_DEFLATED)
    end = data.rfind(b'PK\x05\x06')
    # ZIP64 overrides even non-sentinel ordinary EOCD fields in Python zipfile.
    record = struct.pack('<4sQ2H2I4Q', b'PK\x06\x06', 44, 45, 45, 0, 0, 7, 7, 2 * 1024 * 1024, 0)
    locator = struct.pack('<4sIQI', b'PK\x06\x07', 0, end, 1)
    package = tmp_path / 'zip64-override.zip'
    package.write_bytes(data[:end] + record + locator + data[end:])
    monkeypatch.setattr(zipfile, 'ZipFile', lambda *a, **k: pytest.fail('Parsed ZIP64 override'))
    with pytest.raises(ValueError, match='ZIP64 containers'):
        export.verify_export(package)


@pytest.mark.parametrize('fraction,expected', [(math.nextafter(.07, 1), 8), (.071, 8), (.069, 7)])
def test_budget_keeps_a_genuine_fraction_above_integer_boundary(fraction, expected):
    assert evaluate_budget([False] * 100, review_fraction=fraction)['cases_reviewed'] == expected


def test_budget_retains_exact_rational_support():
    from fractions import Fraction
    assert evaluate_budget([False] * 100, review_fraction=Fraction(7, 100))['cases_reviewed'] == 7


def test_recovery_quarantines_orphan_under_quarantine_named_ancestor(tmp_path):
    from PIL import Image
    from hyunoptic.review.store import ReviewStore
    stream = io.BytesIO()
    Image.new('RGB', (8, 8)).save(stream, format='PNG')
    store = ReviewStore(tmp_path / 'quarantine' / 'workspace' / 'review')
    models = [dict(folder=str(i), identity=str(i), run_id=str(i), weights_sha256=str(i))
              for i in range(2)]
    sid = store.create_session([('source.png', stream.getvalue())], models)
    orphan = store.root / sid / 'predictions' / 'orphan.png'
    orphan.parent.mkdir()
    orphan.write_bytes(b'orphan')
    store.recover(sid)
    assert not orphan.exists()
    assert len(list((store.root / sid / 'quarantine').iterdir())) == 1
    assert store.cases(sid)[0]['input_path'].is_file()
@pytest.mark.parametrize('fraction', [np.int64(1), np.int32(0)])
def test_numeric_integer_budget_results_remain_json_serializable(fraction):
    from hyunoptic.review.validation import evaluate_budget
    result = evaluate_budget([True] * 100, review_fraction=fraction)
    assert type(result['cases_reviewed']) is int
    json.dumps(result, allow_nan=False)

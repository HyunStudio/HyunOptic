"""Private-by-default static review packages and an independent integrity verifier.

Hashes detect accidental/tampered payload changes, not a maliciously replaced manifest.
No original images, label maps, local paths, notes, or actor aliases are exported.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import stat
import tempfile
import zipfile

SCHEMA = 'hyunoptic-review-export-v1'
PAYLOADS = {'session.json', 'cases.csv', 'predictions.csv', 'reviews.csv', 'events.jsonl', 'summary.html'}
MAX_MEMBER_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
METRICS = ('vertical_cdr', 'horizontal_cdr', 'area_cdr', 'disc_vertical_px', 'cup_vertical_px',
           'disc_horizontal_px', 'cup_horizontal_px', 'disc_area_px', 'cup_area_px')


def _json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf-8')


def _cell(value):
    if value is None:
        return ''
    if isinstance(value, (list, dict, tuple)):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    if isinstance(value, str) and (value.lstrip(' \t\r\n').startswith(('=', '+', '-', '@'))
                                   or value.startswith(('\t', '\r', '\n'))):
        return "'" + value
    return value


def _csv(fields, rows) -> bytes:
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows({key: _cell(row.get(key)) for key in fields} for row in rows)
    return stream.getvalue().encode('utf-8')


def _select(row, keys):
    return {key: row.get(key) for key in keys}


def _metric(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def export_session(store, session_id: str, target: Path) -> Path:
    """Export a frozen read-transaction snapshot, with all case statuses in its denominator."""
    snapshot = store.snapshot(session_id)
    session, cases, events = snapshot['session'], snapshot['cases'], snapshot['events']
    public_session = _select(session, ('id', 'schema_version', 'created_utc', 'software_commit',
                                      'input_modality', 'modality', 'protocol_hash', 'status'))
    public_session.update(export_schema=SCHEMA, reference_status='no_reference',
                          total_cases=len(cases), research_only=True)
    public_session['models'] = [dict(_select(m, ('identity', 'run_id', 'weights_sha256')),
        data_status={key: m.get('data_status', {}).get(key) is True for key in ('synthetic', 'partial')}
        if isinstance(m.get('data_status'), dict) else None) for m in session['models']]
    case_rows, prediction_rows, review_rows = [], [], []
    for case in cases:
        row = _select(case, ('id', 'pixel_sha256', 'status', 'prediction_set_hash'))
        row.update(reference_status='no_reference', error_present=bool(case.get('error')),
                   prediction_count=len(case.get('predictions', [])))
        priority = case.get('priority') or {}
        row.update(priority_group=priority.get('group'), priority_score=_metric(priority.get('score')),
                   vcdr_delta=_metric(priority.get('vcdr_delta')))
        case_rows.append(row)
        for prediction in case.get('predictions', []):
            pred = _select(prediction, ('model_identity', 'status', 'run_id', 'weights_sha256', 'labels_sha256'))
            pred.update(case_id=case['id'], reference_status='no_reference',
                        error_count=len(prediction.get('errors') or []))
            measurement = prediction.get('measurement') or {}
            pred.update({key: _metric(measurement.get(key)) for key in METRICS})
            prediction_rows.append(pred)
        review_rows.append(dict(case_id=case['id'], state=case.get('review_state', 'unreviewed'),
                                revision=case.get('revision', 0), prediction_set_hash=case.get('prediction_set_hash'),
                                reasons=case.get('reasons') or []))
    # Event state bodies may contain notes. Export only scalar audit metadata.
    event_rows = [_select(event, ('sequence', 'event_id', 'case_id', 'action', 'old_state', 'new_state',
                                 'prediction_set_hash', 'created_utc', 'timestamp_utc', 'status',
                                 'model_identity', 'input_count')) for event in events]
    for event in event_rows:
        for key in ('old_state', 'new_state'):
            if isinstance(event[key], dict):
                event[key] = event[key].get('review_state', event[key].get('state'))
    counts = {status: sum(case['status'] == status for case in cases)
              for status in sorted({case['status'] for case in cases})}
    rows = ''.join('<tr><td>' + html.escape(str(c['id'])) + '</td><td>' + html.escape(str(c['status']))
                   + '</td><td>' + html.escape(str(c.get('review_state', 'unreviewed'))) + '</td></tr>' for c in cases)
    summary = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Research review summary</title>'
               '<h1>Research review summary</h1><p>Research only. Review records do not certify accuracy. '
               'Reference status: no_reference.</p><p>Total cases: ' + str(len(cases)) + '</p><p>'
               + html.escape(json.dumps(counts, sort_keys=True)) + '</p><table><thead><tr><th>Case</th>'
               '<th>Processing status</th><th>Review state</th></tr></thead><tbody>' + rows + '</tbody></table></html>')
    payloads = {
        'session.json': _json(public_session),
        'cases.csv': _csv(('id', 'pixel_sha256', 'status', 'error_present', 'prediction_count',
                           'prediction_set_hash', 'priority_group', 'priority_score', 'vcdr_delta', 'reference_status'), case_rows),
        'predictions.csv': _csv(('case_id', 'model_identity', 'run_id', 'weights_sha256', 'status',
                                 'error_count', *METRICS, 'labels_sha256', 'reference_status'), prediction_rows),
        'reviews.csv': _csv(('case_id', 'state', 'revision', 'reasons', 'prediction_set_hash'), review_rows),
        'events.jsonl': b''.join(_json(event) for event in event_rows),
        'summary.html': summary.encode('utf-8'),
    }
    payloads['manifest.json'] = _json({'schema': SCHEMA, 'files': [dict(name=name, byte_size=len(data),
        sha256=hashlib.sha256(data).hexdigest()) for name, data in sorted(payloads.items())]})
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.review-export-', suffix='.zip', dir=target.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(payloads.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                archive.writestr(info, data)
        verify_export(Path(temporary))
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def verify_export(path: Path) -> dict:
    """Reject extra/missing/duplicate/unsafe members before reading bounded payloads."""
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            if len(names) != len(set(names)):
                raise ValueError('Duplicate ZIP members')
            if set(names) != PAYLOADS | {'manifest.json'}:
                raise ValueError('Missing, extra, or unsafe ZIP members')
            if sum(m.file_size for m in members) > MAX_TOTAL_BYTES:
                raise ValueError('Export exceeds total size limit')
            for member in members:
                mode = member.external_attr >> 16
                if member.file_size > MAX_MEMBER_BYTES or member.flag_bits & 1 or stat.S_ISLNK(mode):
                    raise ValueError('Unsafe or oversized ZIP member: ' + member.filename)
            manifest = json.loads(archive.read('manifest.json'), object_pairs_hook=_unique_object)
            if not isinstance(manifest, dict) or manifest.get('schema') != SCHEMA:
                raise ValueError('Unsupported export manifest')
            files = manifest.get('files')
            if not isinstance(files, list) or len(files) != len(PAYLOADS):
                raise ValueError('Invalid manifest file list')
            expected = {}
            for item in files:
                if not isinstance(item, dict) or set(item) != {'name', 'byte_size', 'sha256'}:
                    raise ValueError('Invalid manifest member')
                name = item['name']
                if not isinstance(name, str) or name not in PAYLOADS or name in expected:
                    raise ValueError('Unsafe or duplicate manifest member')
                expected[name] = item
            if set(expected) != PAYLOADS:
                raise ValueError('Missing manifest members')
            for name, item in expected.items():
                data = archive.read(name)
                if type(item['byte_size']) is not int or item['byte_size'] != len(data):
                    raise ValueError('Byte size mismatch: ' + name)
                if item['sha256'] != hashlib.sha256(data).hexdigest():
                    raise ValueError('SHA-256 mismatch: ' + name)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid review export: ' + str(exc)) from exc
    return {'valid': True, 'schema': SCHEMA, 'payload_count': len(PAYLOADS)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Verify a HyunOptic research review export ZIP')
    parser.add_argument('zip', type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_export(args.zip)
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

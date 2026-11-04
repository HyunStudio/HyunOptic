"""SQLite-backed local review state with immutable, verified file evidence."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
from uuid import UUID, uuid4

import numpy as np
from PIL import Image

from ..measure import measure_masks

from . import inputs as input_tools
from .inputs import sha256
from .priority import priority

SCHEMA_VERSION = 1
PROTOCOL = {'version': 2, 'ranking': 'error_then_invalid_geometry_then_max_disc_cup_disagreement',
            'tie_break': 'input_ordinal_ascending',
            'input': 'RGB_L_exif_original_resolution', 'reference': 'none'}
REVIEW_REASONS = {'wrong_location', 'boundary_mismatch', 'image_quality',
                  'unsupported_modality', 'uncertain', 'other'}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uuid(value):
    if str(UUID(str(value))) != str(value):
        raise ValueError('Invalid UUID')
    return str(value)


class ReviewStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / 'review.sqlite3'
        with self._db() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise ValueError(f'Unsupported review schema version: {version}')
            if version == 0 and db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                raise ValueError('Unsupported unversioned review schema')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS predictions (case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE, model_identity TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(case_id,model_identity));
                CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, data TEXT NOT NULL);
            ''')
            db.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')

    @contextmanager
    def _db(self, write=False):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.execute('PRAGMA foreign_keys=ON')
        try:
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Artifact path escapes review workspace')
        return path

    def _atomic(self, relative, data):
        target = self._path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.' + uuid4().hex + '.tmp')
        with temporary.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)

    def _session(self, db, sid):
        _uuid(sid)
        row = db.execute('SELECT data FROM sessions WHERE id=?', (sid,)).fetchone()
        if row is None:
            raise ValueError('Unknown session')
        return json.loads(row[0])

    def _case(self, db, cid):
        _uuid(cid)
        row = db.execute('SELECT data FROM cases WHERE id=?', (cid,)).fetchone()
        if row is None:
            raise ValueError('Unknown case')
        return json.loads(row[0])

    def _save_case(self, db, case):
        db.execute('UPDATE cases SET data=? WHERE id=?', (_json(case), case['id']))

    def _event(self, db, case, action, **details):
        event = dict(event_id=str(uuid4()), case_id=case.get('id'), action=action,
                     created_utc=_now(), prediction_set_hash=case.get('prediction_set_hash'), **details)
        db.execute('INSERT INTO events(session_id,data) VALUES (?,?)', (case['session_id'], _json(event)))

    def create_session(self, inputs: list[tuple[str, bytes]], models: list[dict], modality='color_fundus', software_commit='unknown') -> str:
        if not 1 <= len(inputs) <= input_tools.MAX_INPUTS:
            raise ValueError('Session requires 1 to 500 inputs')
        if any(len(data) > input_tools.MAX_FILE_BYTES for _, data in inputs):
            raise ValueError('Input exceeds 30 MB')
        total = sum(len(data) for _, data in inputs)
        if total > input_tools.MAX_TOTAL_BYTES:
            raise ValueError('Inputs exceed 2 GB')
        if shutil.disk_usage(self.root).free < total * 2 + 500 * 1024**2:
            raise ValueError('Insufficient free workspace disk space')
        required = {'folder', 'identity', 'run_id', 'weights_sha256'}
        if len(models) != 2 or any(not required.issubset(m) or any(not isinstance(m[k], str) or not m[k] for k in required) for m in models):
            raise ValueError('Exactly two model identity dictionaries are required')
        if models[0]['identity'] == models[1]['identity']:
            raise ValueError('Two distinct model identities are required')
        if modality not in {'color_fundus', 'slo', 'oct', 'unknown', 'SLO', 'OCT'}:
            raise ValueError('Unknown input modality')
        sid = str(uuid4())
        session = dict(id=sid, schema_version=SCHEMA_VERSION, created_utc=_now(), software_commit=software_commit,
                       modality=modality, input_modality=modality, models=models,
                       protocol=PROTOCOL, protocol_hash=sha256(_json(PROTOCOL).encode()), status='active')
        try:
            with self._db(write=True) as db:
                db.execute('INSERT INTO sessions VALUES (?,?)', (sid, _json(session)))
                for index, (name, data) in enumerate(inputs):
                    cid = str(uuid4())
                    relative = f'{sid}/inputs/{cid}.bin'
                    self._atomic(relative, data)
                    case = dict(id=cid, session_id=sid, ordinal=index, original_name=str(name),
                                input_path=relative, original_sha256=sha256(data), byte_size=len(data),
                                pixel_sha256=None, status='pending', error=None, review_state='unreviewed',
                                revision=0, reasons=[], note='', prediction_set_hash=None)
                    try:
                        case.update(input_tools.inspect_input(data))
                    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
                        case.update(status='error', error=f'Unsupported input: {exc}')
                    db.execute('INSERT INTO cases VALUES (?,?,?)', (cid, sid, _json(case)))
                self._event(db, {'session_id': sid}, 'session_created', input_count=len(inputs))
        except BaseException:
            directory = self._path(sid)
            if directory.exists():
                shutil.rmtree(directory)
            raise
        return sid

    def sessions(self):
        with self._db() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT data FROM sessions ORDER BY rowid')]

    def session(self, session_id):
        with self._db() as db:
            return self._session(db, session_id)

    def _predictions(self, db, case, session):
        found = {row[0]: json.loads(row[1]) for row in db.execute('SELECT model_identity,data FROM predictions WHERE case_id=?', (case['id'],))}
        predictions = []
        for model in session['models']:
            if model['identity'] in found:
                prediction = found[model['identity']]
                if prediction.get('labels_path'):
                    prediction['labels_path'] = self._path(prediction['labels_path'])
                predictions.append(prediction)
        return predictions

    def _verify_input(self, case):
        data = self._path(case['input_path']).read_bytes()
        if sha256(data) != case['original_sha256']:
            raise ValueError('Input artifact hash mismatch')

    def _verify_predictions(self, case, predictions):
        for prediction in predictions:
            if prediction.get('labels_path'):
                path = Path(prediction['labels_path'])
                data = path.read_bytes()
                if sha256(data) != prediction['labels_sha256']:
                    raise ValueError('Prediction artifact hash mismatch')
                with Image.open(io.BytesIO(data)) as image:
                    labels = np.asarray(image)
                if labels.shape != (case.get('height'), case.get('width')) or labels.ndim != 2 or not np.isin(labels, [0, 1, 2]).all():
                    raise ValueError('Prediction artifact geometry mismatch')
            elif prediction['status'] != 'error':
                raise ValueError('Missing prediction artifact')

    def _public_case(self, db, case, session):
        predictions = self._predictions(db, case, session)
        result = dict(case, input_path=self._path(case['input_path']), predictions=predictions)
        try:
            self._verify_input(case)
            self._verify_predictions(case, predictions)
            result['priority'] = priority(predictions)
            if 'artifact_integrity_error' in result['priority'].get('reasons', []):
                raise ValueError('Prediction artifact changed during priority verification')
        except (OSError, ValueError) as exc:
            result.update(status='error', error=f'Evidence integrity error: {exc}', prediction_set_hash=None,
                          review_state='unreviewed', reasons=[], note='', predictions=[], integrity_error=True)
            result['priority'] = dict(group='error', score=None, reasons=['artifact_integrity_error'], vcdr_delta=None)
        if result['status'] == 'error':
            result['priority'] = dict(group='error', score=None, reasons=[result['error'] or 'execution_error'], vcdr_delta=None)
        return result

    def _cases(self, db, sid, session):
        rows = [json.loads(row[0]) for row in db.execute('SELECT data FROM cases WHERE session_id=?', (sid,))]
        return [self._public_case(db, case, session) for case in sorted(rows, key=lambda c: c['ordinal'])]

    def cases(self, session_id):
        with self._db() as db:
            return self._cases(db, session_id, self._session(db, session_id))

    def next_pending(self, session_id):
        """Verify just the next unfinished case; do not decode every queued image."""
        with self._db() as db:
            session = self._session(db, session_id)
            row = db.execute("SELECT data FROM cases WHERE session_id=? AND json_extract(data, '$.status') IN ('pending','interrupted') ORDER BY json_extract(data, '$.ordinal') LIMIT 1", (session_id,)).fetchone()
            return None if row is None else self._public_case(db, json.loads(row[0]), session)

    def _events(self, db, session_id):
        return [dict(json.loads(row[1]), sequence=row[0]) for row in db.execute('SELECT sequence,data FROM events WHERE session_id=? ORDER BY sequence', (session_id,))]

    def events(self, session_id):
        with self._db() as db:
            self._session(db, session_id)
            return self._events(db, session_id)

    def snapshot(self, session_id):
        with self._db() as db:
            session = self._session(db, session_id)
            return dict(session=session, cases=self._cases(db, session_id, session), events=self._events(db, session_id))

    def claim(self, case_id):
        with self._db(write=True) as db:
            case = self._case(db, case_id)
            self._verify_input(case)
            if not case['pixel_sha256']:
                raise ValueError('Unsupported input cannot be claimed')
            if case['status'] == 'processing':
                raise ValueError('Case is already processing')
            if case['status'] == 'complete':
                return False
            token = str(uuid4())
            case.update(status='processing', error=None, claim_token=token)
            self._save_case(db, case)
            self._event(db, case, 'claimed')
        return token

    def _invalidate(self, db, case):
        if case['prediction_set_hash'] or case['review_state'] != 'unreviewed':
            self._event(db, case, 'evidence_invalidated', old_state=case['review_state'], new_state='unreviewed')
            case.update(review_state='unreviewed', reasons=[], note='', revision=case['revision'] + 1)
        case['prediction_set_hash'] = None

    def _check_claim(self, case, claim_token):
        if claim_token is not None and (case.get('claim_token') != claim_token or case['status'] != 'processing'):
            raise ValueError('Stale processing claim; another run recovered or finished this case')

    def record_prediction(self, case_id, model_identity, prediction: dict, labels, *, claim_token=None):
        with self._db(write=True) as db:
            case = self._case(db, case_id)
            self._check_claim(case, claim_token)
            session = self._session(db, case['session_id'])
            models = {m['identity']: m for m in session['models']}
            if model_identity not in models:
                raise ValueError('Unknown model identity')
            self._verify_input(case)
            if prediction.get('status') not in {'ok', 'invalid_geometry', 'error'}:
                raise ValueError('Unsupported prediction status')
            model = models[model_identity]
            for key in ('run_id', 'weights_sha256'):
                if prediction.get(key) and prediction[key] != model[key]:
                    raise ValueError(f'Prediction model {key} mismatch')
            record = dict(prediction, model_identity=model_identity, attempt_id=str(uuid4()),
                          run_id=model['run_id'], weights_sha256=model['weights_sha256'],
                          labels_path=None, labels_sha256=None, created_utc=_now())
            record.setdefault('measurement', None)
            record.setdefault('errors', [])
            record.setdefault('preprocessing', {})
            if not isinstance(record['errors'], list) or any(not isinstance(e, str) for e in record['errors']):
                raise ValueError('Prediction errors must be a list of strings')
            # Labels are the persisted evidence. Never trust adapter-supplied
            # ratios or carry a success measurement beside a failed prediction.
            record['measurement'] = None
            record['measurement_source'] = 'unavailable'
            if labels is not None:
                array = np.asarray(labels)
                if array.ndim != 2 or array.shape != (case['height'], case['width']) or not np.isin(array, [0, 1, 2]).all():
                    raise ValueError('Prediction must be a class map at original resolution')
                if record['status'] == 'ok':
                    try:
                        record['measurement'] = measure_masks(array >= 1, array == 2).to_dict()
                    except ValueError as exc:
                        record['status'] = 'invalid_geometry'
                        record['errors'] = [*record['errors'], f'Stored label geometry invalid: {exc}']
                    else:
                        record['measurement_source'] = 'recomputed_from_saved_labels_v1'
                import io
                stream = io.BytesIO()
                Image.fromarray(array.astype(np.uint8)).save(stream, format='PNG')
                data = stream.getvalue()
                relative = f"{case['session_id']}/predictions/{case_id}/{uuid4()}.png"
                self._atomic(relative, data)
                record.update(labels_path=relative, labels_sha256=sha256(data), labels_byte_size=len(data))
            elif record['status'] != 'error':
                raise ValueError('Successful prediction requires label artifact')
            self._invalidate(db, case)
            case['status'] = 'processing'
            self._save_case(db, case)
            db.execute('INSERT OR REPLACE INTO predictions VALUES (?,?,?)', (case_id, model_identity, _json(record)))
            self._event(db, case, 'prediction_recorded', model_identity=model_identity, status=record['status'])

    def finish(self, case_id, error=None, *, claim_token=None):
        with self._db(write=True) as db:
            case = self._case(db, case_id)
            self._check_claim(case, claim_token)
            session = self._session(db, case['session_id'])
            predictions = self._predictions(db, case, session)
            try:
                self._verify_input(case)
                self._verify_predictions(case, predictions)
            except (OSError, ValueError) as exc:
                error = error or str(exc)
            failures = [str(e) for p in predictions if p['status'] == 'error' for e in p.get('errors', [])]
            if error or failures or len(predictions) != 2 or any(p['status'] == 'error' for p in predictions):
                self._invalidate(db, case)
                case.update(status='error', error=error or '; '.join(failures) or 'Incomplete prediction pair')
            else:
                identity = dict(pixel_sha256=case['pixel_sha256'], models=[m['identity'] for m in session['models']],
                                protocol_hash=session['protocol_hash'], predictions=[{k:v for k,v in p.items() if k not in {'labels_path', 'attempt_id', 'created_utc'}} for p in predictions])
                case.update(status='complete', error=None, prediction_set_hash=sha256(_json(identity).encode()))
            case['claim_token'] = None
            self._save_case(db, case)
            self._event(db, case, 'finished', status=case['status'], error=case['error'])

    def recover(self, session_id):
        with self._db(write=True) as db:
            self._session(db, session_id)
            for row in db.execute('SELECT data FROM cases WHERE session_id=?', (session_id,)).fetchall():
                case = json.loads(row[0])
                if case['status'] == 'processing':
                    case.update(status='pending', error='Interrupted; continue to retry unfinished case', claim_token=None)
                    self._save_case(db, case)
                    self._event(db, case, 'interrupted')
            # Hold the writer lock while quarantining so a newly committed artifact
            # cannot be mistaken for an orphan by another local process.
            referenced = set()
            for row in db.execute('SELECT p.data FROM predictions p JOIN cases c ON p.case_id=c.id WHERE c.session_id=?', (session_id,)):
                value = json.loads(row[0]).get('labels_path')
                if value:
                    referenced.add(self._path(value))
            directory = self._path(session_id)
            if directory.exists():
                orphans = [p for p in directory.rglob('*') if p.is_file()
                           and 'quarantine' not in p.relative_to(directory).parts
                           and (p.suffix == '.tmp' or ('predictions' in p.relative_to(directory).parts
                                                      and p.resolve() not in referenced))]
                for path in orphans:
                    target = self._path(f'{session_id}/quarantine/{uuid4()}-{path.name}')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(path, target)

    def retry(self, case_id):
        """Explicitly retry an operational failure without deleting its event history."""
        with self._db(write=True) as db:
            case = self._case(db, case_id)
            if case['status'] != 'error':
                raise ValueError('Only failed cases can be retried')
            self._verify_input(case)
            if not case['pixel_sha256']:
                raise ValueError('Unsupported input cannot be retried; create a new session')
            self._event(db, case, 'retry_requested', error=case.get('error'))
            self._invalidate(db, case)
            case.update(status='pending', error=None)
            self._save_case(db, case)

    def decide(self, case_id, state, reasons, note, expected_revision):
        reasons = list(reasons)
        if state not in {'unreviewed', 'reviewed', 'held'}:
            raise ValueError('Invalid review state')
        if state == 'held' and not reasons:
            raise ValueError('Held review requires a reason')
        if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
            raise ValueError('Review reasons must be nonempty strings')
        if any(reason not in REVIEW_REASONS for reason in reasons):
            raise ValueError('Unsupported review reason')
        if any(reason.lower() in {'other', '기타'} for reason in reasons) and not note.strip():
            raise ValueError('Other reason requires a note')
        with self._db(write=True) as db:
            case = self._case(db, case_id)
            if case['revision'] != expected_revision:
                raise ValueError('Review revision conflict; refresh before saving')
            if case['status'] != 'complete' or not case['prediction_set_hash']:
                raise ValueError('Review requires a complete prediction set')
            self._verify_input(case)
            predictions = self._predictions(db, case, self._session(db, case['session_id']))
            self._verify_predictions(case, predictions)
            old = {k: case[k] for k in ('review_state', 'reasons', 'note', 'revision')}
            case.update(review_state=state, reasons=reasons, note=note, revision=case['revision'] + 1, updated_utc=_now())
            self._save_case(db, case)
            self._event(db, case, 'review_changed', old_state=old, new_state={k:case[k] for k in old})

    def delete_session(self, session_id):
        with self._db(write=True) as db:
            self._session(db, session_id)
            directory = self._path(_uuid(session_id))
            # Remove private bytes first; a failed removal keeps the database record visible.
            if directory.exists():
                shutil.rmtree(directory)
            export = self._path(f'exports/{session_id}.zip')
            if export.exists():
                export.unlink()
            db.execute('DELETE FROM sessions WHERE id=?', (session_id,))

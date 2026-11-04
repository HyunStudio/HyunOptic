"""Deterministic synthetic metadata/strict-list benchmark; contains no patient data.

Run from the repository with PYTHONPATH=src. Outputs remain under ignored reports/.
The assertions check read scope, not an absolute machine-dependent latency target.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import io
import json
import math
from pathlib import Path
import platform
import sys
import tempfile
import time
from unittest.mock import patch

import numpy as np
from PIL import Image, __version__ as pillow_version

from hyunoptic.review import priority as priority_module
from hyunoptic.review import store as store_module
from hyunoptic.review.store import ReviewStore


def encoded(array):
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format='PNG')
    return buffer.getvalue()


def measure(operation, repeats):
    runs = []
    original_read = Path.read_bytes
    original_hash = store_module.sha256
    for _ in range(repeats):
        counts = dict(artifact_reads=0, artifact_bytes_read=0, sha256_calls=0, bytes_hashed=0)
        def read(path):
            value = original_read(path)
            counts['artifact_reads'] += 1
            counts['artifact_bytes_read'] += len(value)
            return value
        def digest(value):
            counts['sha256_calls'] += 1
            counts['bytes_hashed'] += len(value)
            return original_hash(value)
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'read_bytes', read))
            stack.enter_context(patch.object(store_module, 'sha256', digest))
            stack.enter_context(patch.object(priority_module, 'sha256', digest))
            start = time.perf_counter()
            result = operation()
            elapsed = time.perf_counter() - start
        runs.append(dict(seconds=elapsed, **counts))
    durations = sorted(run['seconds'] for run in runs)
    return dict(median_seconds=float(np.median(durations)),
                p95_seconds=durations[math.ceil(.95 * len(durations)) - 1], runs=runs)


def benchmark(output, sizes=(20, 200), repeats=5, width=128, height=128):
    output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261104)
    source = encoded(rng.integers(0, 256, (height, width, 3), dtype=np.uint8))
    y, x = np.ogrid[:height, :width]
    labels = np.zeros((height, width), dtype=np.uint8)
    distance = (x-width//2)**2 + (y-height//2)**2
    labels[distance <= (min(width,height)*40/128)**2] = 1
    labels[distance <= (min(width,height)*18/128)**2] = 2
    models = [dict(folder='synthetic', identity=f'synthetic-{i}', run_id=f'synthetic-{i}',
                   weights_sha256=str(i)*64) for i in (1, 2)]
    report = dict(synthetic=True, seed=20261104, resolution=[width,height], repeats=repeats,
                  environment=dict(python=sys.version, platform=platform.platform(),
                                   numpy=np.__version__, pillow=pillow_version), sessions=[])
    with tempfile.TemporaryDirectory(prefix='metadata-benchmark-', dir=output) as directory:
        for size in sizes:
            store = ReviewStore(Path(directory) / str(size))
            sid = store.create_session([(f'synthetic-{i:03}.png', source) for i in range(size)], models)
            ids = [case['id'] for case in store.list_case_metadata(sid)]
            for cid in ids:
                token = store.claim(cid)
                for model in models:
                    store.record_prediction(cid, model['identity'], dict(status='ok'), labels, claim_token=token)
                store.finish(cid, claim_token=token)
            metadata = measure(lambda: store.list_case_metadata(sid), repeats)
            strict = measure(lambda: store.cases(sid), repeats)
            selected = measure(lambda: store.verified_case(sid, ids[0]), repeats)
            assert all(run['artifact_reads'] == 0 and run['sha256_calls'] == 0 for run in metadata['runs'])
            assert all(run['artifact_reads'] == 3 and run['sha256_calls'] == 3 for run in selected['runs'])
            report['sessions'].append(dict(inputs=size, source_bytes_each=len(source),
                labels_bytes_each=len(encoded(labels)), total_evidence_bytes=size*(len(source)+2*len(encoded(labels))),
                metadata_list=metadata, strict_list=strict, selected_case=selected,
                metadata_p95_under_half_second=metadata['p95_seconds'] < .5))
    target = output / 'benchmark.json'
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(target.resolve()), sessions=[dict(inputs=s['inputs'],
        metadata_p95_seconds=s['metadata_list']['p95_seconds'], strict_p95_seconds=s['strict_list']['p95_seconds'],
        selected_p95_seconds=s['selected_case']['p95_seconds'],
        metadata_reads=s['metadata_list']['runs'][0]['artifact_reads'],
        strict_reads=s['strict_list']['runs'][0]['artifact_reads'],
        selected_reads=s['selected_case']['runs'][0]['artifact_reads']) for s in report['sessions']]), indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('reports/review_usability_20261104/store'))
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--width', type=int, default=128)
    parser.add_argument('--height', type=int, default=128)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    if min(args.width, args.height) < 8:
        parser.error('image dimensions must each be at least 8')
    benchmark(args.output, repeats=args.repeats, width=args.width, height=args.height)

"""Verify public experiment manifests with the standard library only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re

REQUIRED=('2026-11-03-literature-audit','2026-11-03-first-paper-execution',
          '2026-11-03-issue-remediation','2026-11-04-reader-review-validation')


def unique_pairs(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate manifest key: '+key)
        value[key]=item
    return value


def verify_folder(folder: Path) -> int:
    folder=Path(folder).resolve()
    try:
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'),object_pairs_hook=unique_pairs)
        if not isinstance(manifest,dict):raise ValueError('Manifest must be an object')
        files=manifest.get('files',manifest)
        if not isinstance(files,dict) or not files:raise ValueError('Manifest must list evidence files')
        for name,expected in files.items():
            relative=PurePosixPath(name)
            if (relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name
                    or not relative.parts or relative.as_posix()=='manifest.json'):
                raise ValueError('Unsafe or self-referential manifest path: '+name)
            path=(folder/name).resolve()
            if not path.is_relative_to(folder):raise ValueError('Evidence path leaves its folder')
            if (not isinstance(expected,dict) or type(expected.get('bytes')) is not int
                    or expected['bytes']<0 or not isinstance(expected.get('sha256'),str)
                    or not re.fullmatch('[0-9a-f]{64}',expected['sha256'])):
                raise ValueError('Invalid byte/hash metadata: '+name)
            data=path.read_bytes()
            if len(data)!=expected['bytes'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:
                raise ValueError('Evidence byte/hash mismatch: '+name)
    except OSError as exc:
        raise ValueError(f'Evidence unavailable: {exc}') from exc
    return len(files)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]/'docs'/'experiments')
    args=parser.parse_args()
    folders={args.root/name for name in REQUIRED}
    folders.update(p.parent for p in args.root.glob('*/manifest.json'))
    try:counts=[verify_folder(p) for p in sorted(folders)]
    except ValueError as exc:parser.error(str(exc))
    print(f'Verified {sum(counts)} evidence payloads across {len(counts)} experiment manifests')
    return 0


if __name__=='__main__':raise SystemExit(main())

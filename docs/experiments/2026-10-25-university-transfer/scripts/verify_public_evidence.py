"""Verify published evidence locally or from the staged Git index; no ML dependencies."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git-index',action='store_true')
    args=parser.parse_args()
    folder=Path(__file__).resolve().parents[1]
    root=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=folder,text=True).strip()) if args.git_index else None
    def read(name):
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
            raise ValueError('Unsafe manifest path')
        if args.git_index:
            rel=(folder/Path(name)).relative_to(root).as_posix()
            return subprocess.check_output(['git','show',':'+rel],cwd=root)
        return (folder/Path(name)).read_bytes()
    manifest=json.loads(read('evidence_manifest.json'))
    assert 'evidence_manifest.json' not in manifest
    for name,expected in manifest.items():
        actual=hashlib.sha256(read(name)).hexdigest()
        if actual!=expected:raise ValueError('Evidence SHA256 mismatch: '+name)
    for protocol,runner in [('protocol.json','evaluate_universities.py'),('iowa_protocol.json','evaluate_iowa.py')]:
        expected=json.loads(read(protocol))['runner_sha256']
        if hashlib.sha256(read('scripts/'+runner)).hexdigest()!=expected:
            raise ValueError('Frozen runner SHA256 mismatch: '+runner)
    print(f'Verified {len(manifest)} evidence files and both frozen runners'+(' in staged Git blobs' if args.git_index else ' on disk'))


if __name__=='__main__':main()

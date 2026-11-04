"""CI must detect evidence edits, missing payloads and unsafe manifest paths."""
from pathlib import Path
import hashlib
import json
import runpy

import pytest


def verify():
    return runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts'/'verify_experiment_evidence.py'))['verify_folder']


def fixture(tmp_path,wrapped=True):
    folder=tmp_path/'evidence'
    folder.mkdir()
    (folder/'result.json').write_bytes(b'{"n": 4}\n')
    files={'result.json':{'bytes':9,'sha256':hashlib.sha256(b'{"n": 4}\n').hexdigest()}}
    manifest={'schema':'test','files':files} if wrapped else files
    (folder/'manifest.json').write_text(json.dumps(manifest))
    return folder


@pytest.mark.parametrize('wrapped',[True,False])
def test_evidence_bytes_and_hash_verified_in_supported_layouts(tmp_path,wrapped):
    assert verify()(fixture(tmp_path,wrapped))==1


@pytest.mark.parametrize('mutation',['same_size','missing','wrong_size'])
def test_modified_or_missing_evidence_fails(tmp_path,mutation):
    folder=fixture(tmp_path)
    if mutation=='missing':(folder/'result.json').unlink()
    else:(folder/'result.json').write_bytes(b'{"n": 5}\n' if mutation=='same_size' else b'{}')
    with pytest.raises(ValueError):verify()(folder)


@pytest.mark.parametrize('name',['../outside','/outside','C:/outside','a\\b','manifest.json'])
def test_rejects_unsafe_or_self_referential_paths(tmp_path,name):
    folder=tmp_path/'evidence';folder.mkdir()
    (folder/'manifest.json').write_text(json.dumps({name:{'bytes':0,'sha256':'0'*64}}))
    with pytest.raises(ValueError):verify()(folder)

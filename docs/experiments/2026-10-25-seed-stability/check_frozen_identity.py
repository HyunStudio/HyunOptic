from types import SimpleNamespace
from frozen_identity import assert_frozen_identity

bundle=SimpleNamespace(run_id='frozen-run',weights_sha256='a'*64)
record={'run_id':'frozen-run','weights_sha256':'a'*64}
assert_frozen_identity(bundle,record)
for changed in ({**record,'weights_sha256':'b'*64},{**record,'run_id':'another-run'}):
    try:
        assert_frozen_identity(bundle,changed)
    except AssertionError:
        pass
    else:
        raise AssertionError('A self-consistent replacement bundle must not match a previously frozen identity.')
print('Freeze identity guard accepts original and rejects changed run ID or weights hash.')

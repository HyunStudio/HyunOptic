"""Independent CPU regression checks; requires only installed torch + captured tqdm."""
import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import traceback
from pathlib import Path

import torch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / 'paper_execution_20261103/oxford_mit/DDU/utils/gmm_utils.py'
sys.path.insert(0, str(SOURCE.parents[2] / 'deps'))


def load(path):
    spec = importlib.util.spec_from_file_location('gmm_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checks(module):
    results = []

    def check(name, fn):
        try:
            detail = fn()
            results.append(dict(name=name, passed=True, detail=detail))
        except Exception as exc:
            results.append(dict(name=name, passed=False, error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc()))

    def finite(dtype, kind, magnitude=1.0):
        if kind == 'zero':
            x = torch.zeros(8, 3, dtype=dtype)
        else:
            x = torch.arange(8, dtype=dtype)[:, None].repeat(1, 3) * magnitude
        y = torch.tensor([0] * 4 + [1] * 4)
        model, jitter = module.gmm_fit(x, y, 2)
        values = model.log_prob(x[:, None, :])
        assert torch.isfinite(values).all(), values
        assert model.loc.dtype == dtype
        assert model.covariance_matrix.dtype == dtype
        assert jitter > 0
        return dict(jitter=jitter, log_prob_min=values.min().item(), log_prob_max=values.max().item())

    def fullrank(dtype):
        generator = torch.Generator().manual_seed(814)
        x = torch.randn(60, 4, generator=generator, dtype=dtype)
        y = torch.arange(60) % 2
        model, jitter = module.gmm_fit(x, y, 2)
        means = torch.stack([x[y == c].mean(0) for c in range(2)])
        covs = torch.stack([(x[y == c] - means[c]).T @ (x[y == c] - means[c]) / 29 for c in range(2)])
        expected = torch.distributions.MultivariateNormal(means, covariance_matrix=covs)
        torch.testing.assert_close(model.loc, means)
        torch.testing.assert_close(model.covariance_matrix, covs)
        torch.testing.assert_close(model.log_prob(x[:, None]), expected.log_prob(x[:, None]))
        assert jitter == 0
        return dict(jitter=jitter, max_cov_error=(model.covariance_matrix - covs).abs().max().item())

    def invalid(x, y, count, fragment):
        try:
            module.gmm_fit(x, y, count)
        except ValueError as exc:
            assert fragment in str(exc), str(exc)
            return str(exc)
        raise AssertionError('Expected clear ValueError')

    for dtype in (torch.float32, torch.float64):
        for kind in ('zero', 'rank_deficient'):
            check(f'{dtype}_{kind}_finite', lambda d=dtype, k=kind: finite(d, k))
        check(f'{dtype}_large_rank_deficient_finite', lambda d=dtype: finite(d, 'rank_deficient', 1e10))
        check(f'{dtype}_fullrank_closed_form', lambda d=dtype: fullrank(d))
    x = torch.zeros(4, 2)
    check('missing_class', lambda: invalid(x, torch.zeros(4, dtype=torch.long), 2, 'at least two'))
    check('singleton_class', lambda: invalid(x, torch.tensor([0, 0, 0, 1]), 2, 'at least two'))
    for value in (float('nan'), float('inf'), -float('inf')):
        bad = x.clone()
        bad[0, 0] = value
        check(f'nonfinite_{value}', lambda b=bad: invalid(b, torch.tensor([0, 0, 1, 1]), 2, 'finite'))
    check('label_outside_range', lambda: invalid(x, torch.tensor([0, 0, 2, 2]), 2, 'labels'))
    check('noninteger_labels', lambda: invalid(x, torch.tensor([0., 0., 1., 1.]), 2, 'labels'))
    check('wrong_shape', lambda: invalid(x.flatten(), torch.tensor([0, 0, 1, 1]), 2, 'two-dimensional'))

    def bounded():
        try:
            module.gmm_fit(x, torch.tensor([0, 0, 1, 1]), 2, max_attempts=1)
        except RuntimeError as exc:
            assert '1 attempts' in str(exc) and 'jitter' in str(exc), str(exc)
            return str(exc)
        raise AssertionError('Expected bounded exhaustion error')
    check('bounded_jitter_exhaustion', bounded)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', action='store_true')
    args = parser.parse_args()
    path = SOURCE if args.original else HERE / 'gmm_utils.py'
    torch.set_num_threads(1)
    results = checks(load(path))
    output = dict(source_commit='f597744c65df4ff51615ace5e86e82ffefe1cd0f',
                  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  tested_file=str(path), tested_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  python=platform.python_version(), torch=torch.__version__, device='cpu',
                  passed=sum(r['passed'] for r in results), total=len(results), results=results)
    (HERE / ('original_results.json' if args.original else 'results.json')).write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    sys.exit(0 if all(r['passed'] for r in results) else 1)

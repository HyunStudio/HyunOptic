"""Regressions for mutable local inputs and supported inference boundaries."""
import io
import json
import os
import sys
import types

import pytest
import numpy as np
from PIL import Image

from hyunoptic.seg import BUNDLE_SCHEMA
from hyunoptic.seg.bundle import CONFIG, HISTORY, MANIFEST, SPLIT, WEIGHTS, BundleError, file_sha256, verify_bundle


def make_bundle(folder):
    folder.mkdir()
    for name in (WEIGHTS, CONFIG, SPLIT, HISTORY):
        (folder / name).write_bytes(b'{}')
    manifest = dict(schema=BUNDLE_SCHEMA, run_id='fixture', created_utc='2026-11-03', software_version='1.2.0',
                    architecture=dict(name='unet_small_v1', in_channels=3, n_classes=3, base_channels=4, depth=2),
                    preprocessing=dict(method='letterbox_v1', image_size=64, mean=[.5]*3, std=[.25]*3,
                                       image_interpolation='bilinear', mask_interpolation='nearest'),
                    postprocessing='largest_disc_component_v1 (largest 4-connected disc, cup inside it)',
                    training={}, data_status=dict(synthetic=True, partial=True), permitted_use='Research only',
                    files={name: file_sha256(folder/name) for name in (WEIGHTS, CONFIG, SPLIT, HISTORY)})
    (folder/MANIFEST).write_text(json.dumps(manifest))
    return folder


def test_nested_replacement_invalidates_images_annotations_and_thumbnails(tmp_path):
    from hyunoptic.demo_data import make_papila
    from hyunoptic.ui.state import _mtime, case_data, case_thumb, cases
    root = make_papila(tmp_path/'P', patients=2)
    location = str(root)
    before = _mtime(location)
    ref = cases('PAPILA', location, before)[0]
    old_image, old_readers = case_data(ref, location, before)
    old_thumb = case_thumb(ref, location, before)
    from hyunoptic.papila import discover_cases
    case = discover_cases(root)[0]
    stamp = case.image_path.stat()
    encoded = io.BytesIO()
    Image.new('RGB', old_image.size, 'green').save(encoded, format='JPEG')
    assert len(encoded.getvalue()) <= stamp.st_size
    case.image_path.write_bytes(encoded.getvalue() + b' ' * (stamp.st_size-len(encoded.getvalue())))
    os.utime(case.image_path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    after = _mtime(location)
    # Same length/timestamps can leave the cheap inventory unchanged.
    new_image, _ = case_data(ref, location, after)
    assert new_image.getpixel((0, 0)) != old_image.getpixel((0, 0))
    assert case_thumb(ref, location, after).tobytes() != old_thumb.tobytes()
    contour = case.contour_path('disc', 'exp1')
    stamp = contour.stat()
    contour.write_text(contour.read_text().replace('0', '1'))
    os.utime(contour, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    final = _mtime(location)
    assert final != after
    _, new_readers = case_data(ref, location, final)
    assert not np.array_equal(new_readers[0].disc_xy, old_readers[0].disc_xy)


@pytest.mark.parametrize('field,value', [
    ('architecture', None), ('architecture', {'name':'other'}),
    ('preprocessing', None), ('preprocessing', {'image_size':64}),
    ('postprocessing', 'unsupported'), ('data_status', []),
])
def test_malformed_nested_contracts_raise_bundle_error(tmp_path, field, value):
    folder = make_bundle(tmp_path/'bundle')
    manifest = json.loads((folder/MANIFEST).read_text())
    manifest[field] = value
    (folder/MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(BundleError):
        verify_bundle(folder)


@pytest.mark.parametrize('field,value', [('mean',[0,0,0]), ('std',[0,0,0]), ('image_size',True),
    ('image_size',50), ('image_interpolation','nearest'), ('mask_interpolation','bilinear')])
def test_unsupported_preprocessing_rejected(tmp_path, field, value):
    folder = make_bundle(tmp_path/'bundle')
    manifest = json.loads((folder/MANIFEST).read_text())
    manifest['preprocessing'][field] = value
    (folder/MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(BundleError):
        verify_bundle(folder)


@pytest.mark.parametrize('change', ['config', 'manifest'])
def test_full_bundle_identity_invalidates_both_caches_without_weight_changes(tmp_path, monkeypatch, change):
    from hyunoptic.ui import model_ui
    folder = make_bundle(tmp_path/'bundle')
    class FakePredictor:
        def __init__(self, bundle):
            self.identity = bundle.identity
        def predict(self, image):
            return self.identity
    monkeypatch.setitem(sys.modules, 'hyunoptic.seg.inference', types.SimpleNamespace(Predictor=FakePredictor))
    model_ui.predictor.clear()
    model_ui.predict.clear()
    first = verify_bundle(folder)
    image = Image.new('RGB', (8,8))
    result = model_ui.predict(str(folder), first.identity, 'image', image)
    manifest = json.loads((folder/MANIFEST).read_text())
    if change == 'config':
        (folder/CONFIG).write_bytes(b'{"changed":true}')
        manifest['files'][CONFIG] = file_sha256(folder/CONFIG)
    else:
        manifest['preprocessing']['image_size'] = 96
    (folder/MANIFEST).write_text(json.dumps(manifest))
    second = verify_bundle(folder)
    assert first.weights_sha256 == second.weights_sha256
    assert first.identity != second.identity
    assert model_ui.predict(str(folder), second.identity, 'image', image) != result
    with pytest.raises((ValueError, BundleError)):
        model_ui.predictor.__wrapped__(str(folder), first.identity)


def test_input_refuses_multiframe_tiff_and_unsupported_modes():
    from hyunoptic.ui.input_image import load_input_image
    stream = io.BytesIO()
    Image.new('RGB',(8,8)).save(stream, format='TIFF', save_all=True, append_images=[Image.new('RGB',(8,8))])
    with pytest.raises(ValueError, match='frame'):
        load_input_image(stream.getvalue())
    stream = io.BytesIO()
    Image.new('I',(8,8)).save(stream, format='TIFF')
    with pytest.raises(ValueError, match='mode'):
        load_input_image(stream.getvalue())


def test_input_checks_size_before_pixel_decode_and_applies_exif(monkeypatch):
    from hyunoptic.ui.input_image import load_input_image
    stream = io.BytesIO()
    image = Image.new('L', (8,4), 100)
    exif = Image.Exif()
    exif[274] = 6
    image.save(stream, format='PNG', exif=exif)
    payload = stream.getvalue()
    with pytest.raises(ValueError, match='bytes'):
        load_input_image(payload, max_bytes=len(payload)-1)
    from PIL.PngImagePlugin import PngImageFile
    with monkeypatch.context() as limited:
        def forbidden_decode(*args, **kwargs):
            raise AssertionError('Pixels decoded before dimension limit')
        limited.setattr(PngImageFile, 'load', forbidden_decode)
        with pytest.raises(ValueError, match='pixel'):
            load_input_image(payload, max_pixels=31)
    decoded = load_input_image(payload)
    assert decoded.mode == 'RGB' and decoded.size == (4,8)
    assert decoded.getpixel((0,0)) == (100,100,100)


@pytest.mark.parametrize('section,field,value', [
    ('architecture', 'in_channels', 3.0), ('architecture', 'n_classes', 3.0),
    ('architecture', 'base_channels', True), ('architecture', 'depth', '4'),
    ('preprocessing', 'mean', [10**400, .5, .5]),
    ('preprocessing', 'std', [float('nan'), .25, .25]),
    ('data_status', 'synthetic', 'false'),
])
def test_malformed_numeric_and_boolean_contracts_are_bundle_errors(tmp_path, section, field, value):
    folder = make_bundle(tmp_path/'bundle')
    manifest = json.loads((folder/MANIFEST).read_text())
    manifest[section][field] = value
    (folder/MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(BundleError):
        verify_bundle(folder)


def test_prediction_overlay_respects_contrast_and_line_preferences():
    from hyunoptic.ui.model_ui import draw_prediction
    image = Image.new('RGB', (16,16))
    disc = np.zeros((16,16), bool)
    disc[2:14,2:14] = True
    cup = np.zeros_like(disc)
    cup[5:11,5:11] = True
    _, legend = draw_prediction(image, disc, cup, show_disc=True, show_cup=True,
                                high_contrast=True, dashed_cup=False)
    from hyunoptic.ui.theme import HIGH_CONTRAST
    assert legend == [('Model disc',HIGH_CONTRAST['disc'],'solid'), ('Model cup',HIGH_CONTRAST['cup'],'solid')]

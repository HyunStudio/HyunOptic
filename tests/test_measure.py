import numpy as np
import pytest

from hyunoptic.measure import compare_readers, dice, measure_contours, measure_masks, polygon_mask
from hyunoptic.viz import optic_crop, overlay_contours
from PIL import Image


def square(x1, y1, x2, y2):
    return np.array([[x1,y1], [x2,y1], [x2,y2], [x1,y2]], dtype=float)


def test_exact_square_ratios():
    m = measure_contours(square(2,2,10,10), square(4,4,8,8), (16,16))
    assert m.vertical_cdr == pytest.approx(5/9)
    assert m.horizontal_cdr == pytest.approx(5/9)
    assert m.area_cdr == pytest.approx(25/81)
    assert m.warnings == ()


def test_uses_image_xy_not_swapped():
    m = measure_contours(square(2,3,12,22), square(4,8,8,17), (40,40))
    assert m.vertical_cdr == pytest.approx(10/20)
    assert m.horizontal_cdr == pytest.approx(5/11)


def test_bad_out_of_bounds_and_nonfinite():
    with pytest.raises(ValueError, match="outside"):
        polygon_mask(square(-1,0,5,5), (10,10))
    with pytest.raises(ValueError, match="finite"):
        polygon_mask(np.array([[0,0],[1,np.nan],[2,2.]]), (10,10))


def test_cup_outside_flagged():
    m = measure_contours(square(3,3,11,11), square(8,8,14,14), (20,20))
    assert len(m.warnings) >= 1


def test_inter_reader_comparison():
    d = square(2,2,12,12)
    c = square(4,4,9,9)
    result = compare_readers(d, c, d, c, (20,20))
    assert result["absolute_vcdr_difference"] == 0
    assert result["disc_dice"] == 1
    assert result["cup_dice"] == 1


def test_dice_empty_and_mismatch():
    a = np.zeros((4,4), dtype=bool)
    assert dice(a, a) == 1
    with pytest.raises(ValueError):
        dice(a, np.ones((4,5), bool))


def test_mask_shape_invalid():
    with pytest.raises(ValueError):
        measure_masks(np.zeros((3,3)), np.zeros((4,4)))


def test_overlay_crop_does_not_change_image_geometry():
    img = Image.new("RGB", (32,32))
    disc = square(6,6,20,20)
    cup = square(10,10,15,15)
    out = overlay_contours(img, disc, cup)
    assert out.size == img.size
    crop = optic_crop(out, disc)
    assert 0 < crop.width <= img.width
    assert 0 < crop.height <= img.height

"""Partial-linkage diagnostic from filenames, without guessing unknown patients."""
import zipfile
from hyunoptic.chaksu import scan_test_archive


def test_known_bosch_multi_image_patient_is_not_called_two_independent_people(tmp_path):
    archive = tmp_path / "Test.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for stem in ("P11_image_1", "P11_image_2", "P12_image_1", "UNKNOWN_a"):
            zf.writestr(f"Test/1.0_Original_Fundus_Images/Bosch/{stem}.jpg", b"placeholder")
    cases, report = scan_test_archive(archive)
    assert cases == []  # no original expert masks in this synthetic fixture
    assert report["images_with_partially_decodable_patient_id"] == 3
    assert report["known_repeat_patient_groups"] == 1
    assert report["images_in_known_repeat_groups"] == 2
    assert report["patient_id_linkage_incomplete"] is True
    assert "P11" not in str(report)

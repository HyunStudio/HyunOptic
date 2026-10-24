"""Chaksu TEST zip reader: image and five reader-specific disc/cup TIFF masks.

Built against the original 2023 Scientific Data archive folder specification.
Actual original ZIP compatibility must still be tested. No fused/majority/STAPLE
mask is ever treated as an independent human annotation.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import numpy as np
from PIL import Image

ORIGINAL = "1.0_original_fundus_images"
BINARY = "3.0_doctors_annotations_binary_od_oc"
EXPERTS = tuple(f"expert {i}" for i in range(1, 6))
CAMERAS = ("bosch", "forus", "remidio")
EXPECTED_TEST = {"bosch": 41, "forus": 31, "remidio": 264}
# Some published descriptions say "Test set", some archives use "Test".
TEST_ROOTS = {"test", "test set", "test_set"}
EXPECTED_RESOLUTION = {
    "bosch": {(1920, 1440)},
    "forus": {(2048, 1536)},
    "remidio": {(2448, 3264), (3264, 2448)},
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
MASK_SUFFIXES = {".tif", ".tiff", ".png"}
# Bosch file stems can encode repeated photographs for the same subject:
# P11_image_1 and P11_image_2. Other cameras may have no recoverable ID.
KNOWN_PATIENT_STEM = re.compile(r"^(p\\d+)[_-]", re.IGNORECASE)
MAX_SINGLE_FILE = 160_000_000

def _camera(name: str) -> str:
    norm = name.lower().strip()
    if norm == "remedio":
        norm = "remidio"
    return norm

@dataclass(frozen=True)
class ChaksuCase:
    case_id: str
    camera: str
    image_member: str
    mask_members: dict
    # Index ("expert 1", "disc") etc. The database's "OD" is OPTIC DISC.
    def mask_member(self, expert: str, structure: str) -> str:
        return self.mask_members[(expert, structure)]

def scan_test_archive(path: str | Path) -> tuple[list[ChaksuCase], dict]:
    """Index archive paths and warn on incomplete or ambiguous images/annotations.

    No bytes extracted, and no fabricated labels inferred from fusion masks.
    """
    path = Path(path)
    if not zipfile.is_zipfile(path):
        raise ValueError("Expected a locally obtained official Chaksu Test.zip")
    images, masks = {}, {}
    duplicate = []
    sizes = []
    suspicious = []
    with zipfile.ZipFile(path) as zf:
        entries = [v for v in zf.infolist() if not v.is_dir()]
        for entry in entries:
            if entry.flag_bits & 0x1 or entry.file_size > MAX_SINGLE_FILE:
                suspicious.append({"member": entry.filename, "reason": "encrypted or oversize"})
                continue
            sizes.append((entry.filename, int(entry.file_size)))
            parts = PurePosixPath(entry.filename.replace("\\", "/")).parts
            lowered = [s.lower() for s in parts]
            if ORIGINAL in lowered:
                i = lowered.index(ORIGINAL)
                if len(parts) <= i + 2 or PurePosixPath(parts[-1]).suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                if not any(part in TEST_ROOTS for part in lowered[:i]):
                    continue  # never use Train as external holdout
                cam = _camera(parts[i + 1])
                if cam not in CAMERAS:
                    continue
                key = (cam, PurePosixPath(parts[-1]).stem.lower())
                if key in images:
                    duplicate.append(str(key))
                images[key] = entry.filename
            elif BINARY in lowered:
                i = lowered.index(BINARY)
                if len(parts) <= i + 4 or PurePosixPath(parts[-1]).suffix.lower() not in MASK_SUFFIXES:
                    continue
                if not any(part in TEST_ROOTS for part in lowered[:i]):
                    continue
                expert = lowered[i + 1]
                cam = _camera(parts[i + 2])
                structure = lowered[i + 3].strip()
                if expert not in EXPERTS or cam not in CAMERAS or structure not in {"disc", "cup"}:
                    continue
                key = (cam, PurePosixPath(parts[-1]).stem.lower(), expert, structure)
                if key in masks:
                    duplicate.append(str(key))
                masks[key] = entry.filename
    cases, missing = [], []
    for (cam, stem), image_member in sorted(images.items()):
        found = {(expert, structure): masks.get((cam, stem, expert, structure))
                 for expert in EXPERTS for structure in ("disc", "cup")}
        absent = [f"{reader}/{structure}" for (reader, structure), member in found.items() if member is None]
        if absent:
            missing.append({"case_id": f"{cam}/{stem}", "missing": absent})
        else:
            cases.append(ChaksuCase(f"{cam}/{stem}", cam, image_member, found))
    # Do not mistake consecutive photographs for independent subjects.
    # This is only a partial linkage, NOT complete unique-patient identification.
    known_groups = {}
    for cam, stem in images:
        matched = KNOWN_PATIENT_STEM.match(stem)
        if matched:
            known_groups.setdefault((cam, matched.group(1).lower()), 0)
            known_groups[(cam, matched.group(1).lower())] += 1
    camera_counts = {cam: sum(c.camera == cam for c in cases) for cam in CAMERAS}
    fingerprint = hashlib.sha256(json.dumps({
        "images": sorted(images.items()), "masks": sorted(masks.items()),
        "entry_names_and_sizes": sorted(sizes),
    }, sort_keys=True).encode()).hexdigest()
    complete = (camera_counts == EXPECTED_TEST and len(images) == 336
                and len(cases) == 336 and not duplicate and not suspicious)
    manifest = {
        "dataset": "Chaksu", "study_partition": "published Test only",
        "source": "local ZIP; no upload of eye images",
        "published_test_counts": EXPECTED_TEST,
        "image_entries": len(images),
        "complete_5_reader_cases": len(cases),
        "images_with_partially_decodable_patient_id": sum(known_groups.values()),
        "known_repeat_patient_groups": sum(n > 1 for n in known_groups.values()),
        "images_in_known_repeat_groups": sum(n for n in known_groups.values() if n > 1),
        "patient_id_linkage_incomplete": True,

        "readable_case_counts_by_camera": camera_counts,
        "missing_annotation_cases": missing,
        "ambiguous_duplicate_members": duplicate,
        "suspicious_members": suspicious,
        "matches_published_test_file_layout": complete,
        "metadata_path_fingerprint_only": fingerprint,
        "fingerprint_uses_entry_names_and_uncompressed_sizes": True,
        "note": "File count and names do not establish correct mask semantics or external validity.",
    }
    return cases, manifest

def _read_member(zf: zipfile.ZipFile, name: str) -> Image.Image:
    meta = zf.getinfo(name)
    if meta.file_size > MAX_SINGLE_FILE:
        raise ValueError("Archive image/mask entry exceeds safety limit")
    # Bound uncompressed memory before PIL decodes the payload.
    with zf.open(name) as stream:
        content = stream.read(MAX_SINGLE_FILE + 1)
    if len(content) > MAX_SINGLE_FILE:
        raise ValueError("Exceeded maximum image/mask payload length")
    with Image.open(io.BytesIO(content)) as obj:
        obj.load()
        return obj.copy()

def load_test_case(zf: zipfile.ZipFile, case: ChaksuCase,
                   *, readers: tuple[str, ...] = ("expert 1", "expert 2")) -> tuple[Image.Image, dict]:
    image = _read_member(zf, case.image_member).convert("RGB")
    masks = {}
    for reader in readers:
        if reader not in EXPERTS:
            raise ValueError("Expected original human expert 1..5")
        for structure in ("disc", "cup"):
            raw = np.asarray(_read_member(zf, case.mask_member(reader, structure)).convert("L"), dtype=np.uint8)
            if raw.shape != (image.height, image.width):
                raise ValueError(f"{reader}/{structure} resolution mismatch")
            levels = np.unique(raw)
            if len(levels) > 2 or 0 not in levels or raw.max() == 0:
                raise ValueError(f"{reader}/{structure} is not a nonempty binary zero-background mask")
            masks[(reader, structure)] = raw > 0
        disc, cup = masks[(reader, "disc")], masks[(reader, "cup")]
        if np.any(cup & ~disc):
            raise ValueError(f"{reader} optic cup extends beyond disc mask")
    return image, masks

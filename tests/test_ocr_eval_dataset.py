"""ocr_eval: dataset manifests, validation, loading, and the committed datasets."""

import json

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from ocr_eval import DATASETS_DIR  # noqa: E402
from ocr_eval.dataset import (  # noqa: E402
    DatasetError,
    assign_split,
    list_datasets,
    load_dataset,
    read_image,
    resolve_dataset,
    validate_dataset,
)

COMMITTED = ["synthetic_7seg", "textocr_scoreboards"]


def _row(**overrides):
    row = {
        "id": "a1",
        "image": "images/a1.png",
        "text": "12",
        "field_type": "score",
        "display_tech": "led7",
        "split": "test",
        "label_source": "human",
        "license": "CC0-1.0",
        "source_url": None,
        "author": "someone",
        "attribution": "someone (CC0-1.0)",
        "source_box": [1, 2, 30, 20],
        "notes": "",
    }
    row.update(overrides)
    return row


def make_dataset(folder, rows, image=None, license_files=True):
    (folder / "images").mkdir(parents=True, exist_ok=True)
    if image is None:
        image = np.zeros((20, 30), np.uint8)
    for row in rows:
        path = folder / row["image"]
        if path.suffix == ".png" and ".." not in row["image"]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(cv2.imencode(".png", image)[1].tobytes())
    (folder / "manifest.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    if license_files:
        (folder / "LICENSE").write_text("CC0", encoding="utf-8")
        (folder / "ATTRIBUTION.md").write_text("none", encoding="utf-8")
    return folder


@pytest.mark.parametrize("name", COMMITTED)
def test_committed_datasets_are_valid_and_redistributable(name):
    report = validate_dataset(DATASETS_DIR / name, strict_licenses=True)
    assert report.ok, report.errors[:10]
    dataset = load_dataset(name)
    assert len(dataset) > 0
    for sample in dataset.samples:
        assert sample.attribution, sample.id
        assert sample.author, sample.id


def test_committed_real_dataset_is_human_labelled_and_attributed():
    dataset = load_dataset("textocr_scoreboards")
    assert len(dataset) >= 300
    sources = {s.label_source for s in dataset.samples}
    assert "synthetic" not in sources
    for sample in dataset.samples:
        assert sample.source_url and sample.source_url.startswith("https://"), sample.id
        assert sample.source_box is not None
    total = sum((dataset.path / s.image).stat().st_size for s in dataset.samples)
    assert total < 15e6


def test_list_datasets_includes_committed():
    names = {path.name for path in list_datasets()}
    assert set(COMMITTED) <= names


def test_valid_dataset_loads(tmp_path):
    folder = make_dataset(
        tmp_path / "ds", [_row(), _row(id="a2", image="images/a2.png", split="dev")]
    )
    dataset = load_dataset(folder)
    assert dataset.name == "ds"
    assert [s.id for s in dataset.samples] == ["a1", "a2"]
    assert dataset.samples[0].source_box == (1, 2, 30, 20)
    assert len(load_dataset(folder, splits=["dev"])) == 1
    assert len(load_dataset(folder, limit=1)) == 1
    # by manifest path, and by name through OCR_EVAL_DATASETS
    assert resolve_dataset(folder / "manifest.jsonl") == folder.resolve()


def test_dataset_by_name_from_environment(tmp_path, monkeypatch):
    make_dataset(tmp_path / "private_set", [_row()])
    monkeypatch.setenv("OCR_EVAL_DATASETS", str(tmp_path))
    assert resolve_dataset("private_set") == (tmp_path / "private_set").resolve()
    assert "private_set" in {p.name for p in list_datasets()}


def test_unknown_dataset(tmp_path):
    with pytest.raises(DatasetError):
        resolve_dataset(str(tmp_path / "nope"))


def test_extra_keys_are_kept(tmp_path):
    folder = make_dataset(tmp_path / "ds", [_row(word_box=[1, 1, 5, 5])])
    [sample] = load_dataset(folder).samples
    assert sample.extra == {"word_box": [1, 1, 5, 5]}
    assert sample.to_dict()["word_box"] == [1, 1, 5, 5]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"field_type": "scores"}, "field_type"),
        ({"display_tech": "neon"}, "display_tech"),
        ({"split": "val"}, "split"),
        ({"label_source": "me"}, "label_source"),
        ({"text": ""}, "empty text"),
        ({"text": " 12"}, "whitespace"),
        ({"id": "a b"}, "invalid id"),
        ({"image": "../x.png"}, "relative path"),
        ({"image": "images/a1.jpg"}, ".png"),
        ({"source_box": [1, 2, 0, 3]}, "source_box"),
        ({"license": ""}, "empty license"),
        ({"text": 12}, "must be a string"),
    ],
)
def test_invalid_rows(tmp_path, overrides, message):
    folder = make_dataset(tmp_path / "ds", [_row(**overrides)])
    report = validate_dataset(folder)
    assert not report.ok
    assert any(message in error for error in report.errors), report.errors
    with pytest.raises(DatasetError):
        load_dataset(folder)


def test_missing_field_and_duplicate_id(tmp_path):
    row = _row()
    del row["split"]
    folder = make_dataset(tmp_path / "ds", [row, _row(), _row()])
    errors = validate_dataset(folder).errors
    assert any("missing 'split'" in e for e in errors)
    assert any("duplicate id" in e for e in errors)


def test_missing_image_and_license_files(tmp_path):
    folder = make_dataset(tmp_path / "ds", [_row()], license_files=False)
    (folder / "images" / "a1.png").unlink()
    errors = validate_dataset(folder).errors
    assert any("missing image" in e for e in errors)
    assert any("LICENSE" in e for e in errors)
    assert any("ATTRIBUTION" in e for e in errors)


def test_non_redistributable_license(tmp_path):
    folder = make_dataset(tmp_path / "ds", [_row(license="LicenseRef-private")])
    report = validate_dataset(folder)
    assert report.ok and report.warnings
    assert not validate_dataset(folder, strict_licenses=True).ok


def test_read_image_always_gives_bgr_uint8(tmp_path):
    gray = np.arange(200, dtype=np.uint8).reshape(10, 20)
    cv2.imwrite(str(tmp_path / "g.png"), gray)
    image = read_image(tmp_path / "g.png")
    assert image.shape == (10, 20, 3) and image.dtype == np.uint8
    rgba = np.zeros((4, 5, 4), np.uint8)
    cv2.imwrite(str(tmp_path / "a.png"), rgba)
    assert read_image(tmp_path / "a.png").shape == (4, 5, 3)
    deep = (np.arange(20, dtype=np.uint16) * 1000).reshape(4, 5)
    cv2.imwrite(str(tmp_path / "d.png"), deep)
    assert read_image(tmp_path / "d.png").dtype == np.uint8


def test_assign_split_is_stable():
    assert assign_split("photo1") == assign_split("photo1")
    splits = {assign_split(f"photo{i}") for i in range(100)}
    assert splits == {"dev", "test"}

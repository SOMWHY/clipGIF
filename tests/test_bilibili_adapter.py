import pytest

from app.platforms.bilibili import BilibiliAdapter


@pytest.fixture
def adapter():
    return BilibiliAdapter()


def test_default_format_prefers_480p_then_falls_back_to_best(adapter):
    assert adapter.get_default_format() == (
        "bv*[height<=480]+ba/b[height<=480]/bv*+ba/b"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("BV1xx411c7mD", "https://www.bilibili.com/video/BV1xx411c7mD"),
        ("https://www.bilibili.com/video/BV1xx411c7mD?p=1", "https://www.bilibili.com/video/BV1xx411c7mD"),
    ],
)
def test_normalizes_bv_and_full_url(adapter, raw, expected):
    assert adapter.match(raw)
    assert adapter.normalize(raw) == expected
    assert adapter.extract_video_id(expected) == "BV1xx411c7mD"


def test_short_url_follows_only_allowed_redirect(adapter, monkeypatch):
    monkeypatch.setattr(
        adapter,
        "_resolve_short_url",
        lambda _url: "https://www.bilibili.com/video/BV1xx411c7mD",
    )
    assert adapter.match("https://b23.tv/abcd")
    assert adapter.normalize("https://b23.tv/abcd") == "https://www.bilibili.com/video/BV1xx411c7mD"


def test_short_url_rejects_other_hosts(adapter, monkeypatch):
    monkeypatch.setattr(adapter, "_resolve_short_url", lambda _url: "https://example.com/BV1xx411c7mD")
    with pytest.raises(ValueError, match="短链"):
        adapter.normalize("https://b23.tv/abcd")


@pytest.mark.parametrize(
    "raw",
    [
        "not-a-bv",
        "https://example.com/video/BV1xx411c7mD",
        "https://user@b23.tv/short",
        "https://b23.tv:8080/short",
    ],
)
def test_invalid_inputs_are_rejected(adapter, raw):
    assert not adapter.match(raw)
    with pytest.raises(ValueError):
        adapter.normalize(raw)

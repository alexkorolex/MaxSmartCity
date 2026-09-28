import pytest

from src.domains.reports.images import sniff_image_type


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n\x00\x00", "image/png"),
        (b"RIFF\x24\x00\x00\x00WEBPVP8 ", "image/webp"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", None),
        (b"<html><script>alert(1)</script>", None),
        (b"GIF89a", None),
        (b"", None),
    ],
)
def test_image_type_comes_from_the_file_bytes(content: bytes, expected: str | None) -> None:
    assert sniff_image_type(content) == expected

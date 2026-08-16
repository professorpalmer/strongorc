from __future__ import annotations

from pathlib import Path

import pytest

from ink import parse


def test_sections_ints_and_override() -> None:
    text = "port = 1\n[db]\nhost = local\nport = 2\nport = 3\n"
    data = parse(text)
    assert data["port"] == 1
    assert data["db.host"] == "local"
    assert data["db.port"] == 3


def test_interpolation_and_include(tmp_path: Path) -> None:
    (tmp_path / "base.cfg").write_text("name = oak\n", encoding="utf-8")
    text = "${include:base.cfg}\ngreet = hi ${name}\n"
    data = parse(text, root=tmp_path)
    assert data["name"] == "oak"
    assert data["greet"] == "hi oak"


def test_circular_include_raises(tmp_path: Path) -> None:
    (tmp_path / "a.cfg").write_text("${include:b.cfg}\n", encoding="utf-8")
    (tmp_path / "b.cfg").write_text("${include:a.cfg}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse("${include:a.cfg}\n", root=tmp_path)


def test_comments_and_quoted_false() -> None:
    data = parse('flag = false\n# ignore\nname = "a = b"\n')
    assert data["flag"] is False
    assert data["name"] == "a = b"


def test_json_loads_is_wrong() -> None:
    data = parse("ok = true\n")
    assert data == {"ok": True}

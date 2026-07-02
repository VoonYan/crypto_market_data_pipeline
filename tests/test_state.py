"""Unit tests for the incremental watermark logic."""
import json

from ingestion import state


def test_load_missing_state_returns_empty(tmp_path):
    assert state.load_state(tmp_path / "nope.json") == {}


def test_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    st = {"bitcoin": 1700000000}
    state.save_state(path, st)
    assert state.load_state(path) == st
    assert json.loads(path.read_text())["bitcoin"] == 1700000000


def test_watermark_never_moves_backwards():
    st = {"bitcoin": 200}
    state.set_watermark(st, "bitcoin", 100)
    assert st["bitcoin"] == 200
    state.set_watermark(st, "bitcoin", 300)
    assert st["bitcoin"] == 300


def test_new_coin_gets_none_watermark():
    assert state.get_watermark({}, "ethereum") is None

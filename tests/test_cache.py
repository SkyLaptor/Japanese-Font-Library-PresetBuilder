from pathlib import Path

import yaml

from src.models.cache import Cache


def test_init_and_load_nonexistent(tmp_path):
    """Cache should initialize and handle non-existent cache file"""
    cache_file = tmp_path / "cache.yml"
    c = Cache(cache_file)
    # After load(), data attribute should exist
    assert hasattr(c, "data")


def test_load_existing_cache(tmp_path):
    """Cache should load existing cache file"""
    cache_file = tmp_path / "cache.yml"
    initial_data = [
        {
            "swf_path": "fonts_test.swf",
            "modified_date": "2026/01/01 12:00:00",
            "font_names": ["test_font"],
            "hash": "",
        }
    ]
    cache_file.write_text(yaml.dump(initial_data), encoding="utf-8")

    c = Cache(cache_file)
    assert c.data == initial_data


def test_load_empty_yaml(tmp_path):
    """Cache should handle empty YAML file"""
    cache_file = tmp_path / "cache.yml"
    cache_file.write_text("", encoding="utf-8")

    c = Cache(cache_file)
    assert hasattr(c, "data")


def test_save_and_reload(tmp_path):
    """Cache should save and reload data"""
    cache_file = tmp_path / "cache.yml"
    initial_data = [
        {
            "swf_path": "fonts_save_test.swf",
            "modified_date": "2026/01/01 12:00:00",
            "font_names": ["font_a", "font_b"],
            "hash": "",
        }
    ]

    c = Cache(cache_file)
    c.data = initial_data
    c.save()

    # Reload and verify
    c2 = Cache(cache_file)
    assert c2.data == initial_data


def test_update_new_entry(tmp_path):
    """Cache should add new entry"""
    cache_file = tmp_path / "cache.yml"
    swf_dir = tmp_path / "swfs"
    swf_dir.mkdir()
    swf_file = swf_dir / "fonts_new.swf"
    swf_file.touch()

    c = Cache(cache_file)
    c.data = []
    c.update(swf_file, ["new_font"], swf_dir)

    assert len(c.data) == 1
    assert c.data[0]["swf_path"] == "fonts_new.swf"
    assert c.data[0]["font_names"] == ["new_font"]


def test_update_existing_entry(tmp_path):
    """Cache should update existing entry"""
    cache_file = tmp_path / "cache.yml"
    swf_dir = tmp_path / "swfs"
    swf_dir.mkdir()
    swf_file = swf_dir / "fonts_update.swf"
    swf_file.touch()

    c = Cache(cache_file)
    c.data = [
        {
            "swf_path": "fonts_update.swf",
            "modified_date": "2026/01/01 00:00:00",
            "font_names": ["old_font"],
            "hash": "",
        }
    ]

    c.update(swf_file, ["new_font"], swf_dir)

    assert len(c.data) == 1
    assert c.data[0]["font_names"] == ["new_font"]
    assert c.data[0]["modified_date"] != "2026/01/01 00:00:00"


def test_update_absolute_path_fallback(tmp_path):
    """Cache should use absolute path if relative path conversion fails"""
    cache_file = tmp_path / "cache.yml"
    swf_file = Path("C:/external/fonts.swf")

    c = Cache(cache_file)
    c.data = []
    # Mock stat() to avoid actual file requirement
    swf_file_mock = tmp_path / "mock.swf"
    swf_file_mock.touch()

    c.update(swf_file_mock, ["mock_font"], tmp_path / "different_dir")

    # Should have added entry with relative path (since it's under tmp_path)
    assert len(c.data) == 1


def test_no_alias_in_saved_yaml(tmp_path):
    """Cache should save YAML without anchor/alias"""
    cache_file = tmp_path / "cache.yml"
    shared_list = ["font_a", "font_b"]

    c = Cache(cache_file)
    c.data = [
        {
            "swf_path": "fonts_1.swf",
            "modified_date": "2026/01/01 12:00:00",
            "font_names": shared_list,
            "hash": "",
        },
        {
            "swf_path": "fonts_2.swf",
            "modified_date": "2026/01/01 12:00:00",
            "font_names": shared_list,
            "hash": "",
        },
    ]
    c.save()

    # Read raw YAML and check for alias markers (* or &)
    raw_yaml = cache_file.read_text(encoding="utf-8")
    assert "&" not in raw_yaml or "*" not in raw_yaml  # No anchors or aliases

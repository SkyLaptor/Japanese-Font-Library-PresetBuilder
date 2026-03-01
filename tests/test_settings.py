import yaml

import src.models.settings as settings_mod
from src.models.settings import Settings


def test_init_loads_template_when_missing(tmp_path, monkeypatch):
    """Settings should load template when file doesn't exist"""
    template = tmp_path / "template.yml"
    template.write_text(yaml.dump({"foo": "bar"}), encoding="utf-8")
    monkeypatch.setattr(settings_mod, "TEMPLATE_SETTINGS_FILE", template)

    settings_file = tmp_path / "settings.yml"
    s = Settings(settings_file)
    # After load(), template data is used since file doesn't exist
    assert s.data == {"foo": "bar"}


def test_init_loads_existing_file(tmp_path):
    """Settings should load existing file and add missing fields"""
    settings_file = tmp_path / "settings.yml"
    content = {"last_preset": "preset1", "swf_dir": "/path/to/swf"}
    settings_file.write_text(yaml.dump(content), encoding="utf-8")

    s = Settings(settings_file)
    # load() automatically adds missing output_dir
    assert s.data["last_preset"] == "preset1"
    assert s.data["swf_dir"] == "/path/to/swf"
    assert s.data["output_dir"] == ""


def test_load_compatibility_transforms(tmp_path):
    """load() should apply compatibility transformations for old config format"""
    settings_file = tmp_path / "settings.yml"
    content = {
        "weight_type": ["Normal", "Bold"],
        "last_preset_name": "old_preset",
    }
    settings_file.write_text(yaml.dump(content), encoding="utf-8")

    s = Settings(settings_file)
    s.load()

    # weight_type should be extracted and stored as attribute
    assert hasattr(s, "weight_type") and s.weight_type == ["Normal", "Bold"]
    # last_preset_name should be renamed to last_preset
    assert s.data["last_preset"] == "old_preset"
    assert "last_preset_name" not in s.data


def test_load_adds_missing_dirs(tmp_path):
    """load() should add missing swf_dir and output_dir fields"""
    settings_file = tmp_path / "settings.yml"
    content = {"last_preset": "test"}
    settings_file.write_text(yaml.dump(content), encoding="utf-8")

    s = Settings(settings_file)
    s.load()

    assert s.data["swf_dir"] == ""
    assert s.data["output_dir"] == ""


def test_property_getters_setters(tmp_path):
    """Properties should get and set values correctly"""
    settings_file = tmp_path / "settings.yml"
    content = {
        "last_preset": "old",
        "swf_dir": "/old/swf",
        "output_dir": "/old/out",
    }
    settings_file.write_text(yaml.dump(content), encoding="utf-8")

    s = Settings(settings_file)

    assert s.last_preset == "old"
    assert s.swf_dir == "/old/swf"
    assert s.output_dir == "/old/out"

    s.last_preset = "new"
    s.swf_dir = "/new/swf"
    s.output_dir = "/new/out"

    assert s.last_preset == "new"
    assert s.swf_dir == "/new/swf"
    assert s.output_dir == "/new/out"


def test_property_getters_default_to_empty_string(tmp_path):
    """Properties should return empty string if key doesn't exist"""
    settings_file = tmp_path / "settings.yml"
    settings_file.write_text(yaml.dump({}), encoding="utf-8")

    s = Settings(settings_file)
    # load() adds missing fields
    assert s.last_preset == ""
    assert s.swf_dir == ""
    assert "output_dir" in s.data
    assert isinstance(s.output_dir, str)


def test_save(tmp_path):
    """save() should write data to YAML file"""
    settings_file = tmp_path / "settings.yml"
    s = Settings(settings_file)
    s.data = {
        "last_preset": "test",
        "swf_dir": "/path",
        "output_dir": "/out",
    }
    s.save()

    loaded = yaml.safe_load(settings_file.read_text(encoding="utf-8"))
    assert loaded["last_preset"] == "test"
    assert loaded["swf_dir"] == "/path"
    assert loaded["output_dir"] == "/out"


def test_swf_dir_is_stored_as_given_path_string(tmp_path):
    """Settings should store swf_dir as-is without path conversion logic"""
    settings_file = tmp_path / "settings.yml"
    s = Settings(settings_file)

    expected_path = "C:/game/mods/fonts"
    s.swf_dir = expected_path
    s.save()

    loaded = Settings(settings_file)
    assert loaded.swf_dir == expected_path


def test_last_preset_keeps_relative_name_as_given(tmp_path):
    """last_preset should keep preset-relative name as-is"""
    settings_file = tmp_path / "settings.yml"
    s = Settings(settings_file)

    expected = "example.yml"
    s.last_preset = expected
    s.save()

    loaded = Settings(settings_file)
    assert loaded.last_preset == expected


def test_output_dir_is_stored_as_given_absolute_path_string(tmp_path):
    """output_dir should be stored as given without conversion"""
    settings_file = tmp_path / "settings.yml"
    s = Settings(settings_file)

    expected = "C:/mods/output"
    s.output_dir = expected
    s.save()

    loaded = Settings(settings_file)
    assert loaded.output_dir == expected


def test_migrated_flag_is_false_when_no_legacy_transform_needed(tmp_path):
    """migrated should be False if no legacy key conversion or completion occurs"""
    settings_file = tmp_path / "settings.yml"
    settings_file.write_text(
        yaml.dump(
            {
                "last_preset": "default.yml",
                "swf_dir": "C:/swf",
                "output_dir": "C:/out",
            }
        ),
        encoding="utf-8",
    )

    s = Settings(settings_file)
    assert s.migrated is False

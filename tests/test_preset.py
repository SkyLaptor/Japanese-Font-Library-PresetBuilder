import yaml

import src.models.preset as preset_mod
from src.models.preset import Preset


def test_init_loads_template_when_missing(tmp_path, monkeypatch):
    template = tmp_path / "template.yml"
    template.write_text(yaml.dump({"foo": "bar"}), encoding="utf-8")
    monkeypatch.setattr(preset_mod, "TEMPLATE_PRESET_FILE", template)

    p = Preset(tmp_path / "nonexistent.yml")
    assert p.data == {"foo": "bar"}


def test_load_compatibility_and_getters(tmp_path):
    preset_file = tmp_path / "preset.yml"
    content = {
        "swf_dir": "S",
        "output_dir": "O",
        "fontlibs": ["A"],
        "valid_name_chars": "ABC",
        "mappings": [{"map_name": "m1", "font_name": "F1"}],
    }
    preset_file.write_text(yaml.dump(content), encoding="utf-8")

    p = Preset(preset_file)
    # load() applies compatibility transforms
    p.load()

    assert hasattr(p, "swf_dir") and p.swf_dir == "S"
    assert hasattr(p, "output_dir") and p.output_dir == "O"
    assert hasattr(p, "fontlibs") and p.fontlibs == ["A"]
    assert p.data["validnamechars"] == "ABC"
    assert p.data["mappings"][0]["swf_path"] == ""

    assert p.get_mapping_swf_path("m1") == ""
    assert p.get_mapping_font_name("m1") == "F1"
    assert p.get_mapping_swf_path("missing") == ""


def test_property_setters_getters_and_save(tmp_path):
    preset_file = tmp_path / "preset.yml"
    base = {"mappings": [{"map_name": "a", "font_name": "b"}], "validnamechars": "x"}
    preset_file.write_text(yaml.dump(base), encoding="utf-8")

    p = Preset(preset_file)
    p.mappings = [{"map_name": "x", "font_name": "y"}]
    assert p.mappings[0]["map_name"] == "x"
    p.validnamechars = "z"
    assert p.validnamechars == "z"

    p.save()
    new = yaml.safe_load(preset_file.read_text(encoding="utf-8"))
    assert new["mappings"][0]["map_name"] == "x"
    assert new["validnamechars"] == "z"


def test_mappings_base_group_is_migrated_to_category(tmp_path):
    preset_file = tmp_path / "preset.yml"
    content = {
        "valid_name_chars": "ABC",
        "mappings": [
            {
                "map_name": "$ConsoleFont",
                "base_group": "console",
                "font_name": "F1",
            }
        ],
    }
    preset_file.write_text(yaml.dump(content), encoding="utf-8")

    p = Preset(preset_file)
    p.load()

    assert p.data["mappings"][0]["category"] == "console"
    assert p.data["mappings"][0]["swf_path"] == ""

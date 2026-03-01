import yaml

import src.models.preset as preset_mod
from src.models.preset import Preset


def _template_data():
    return {
        "validnamechars": "DEFAULT_CHARS",
        "mappings": [
            {
                "map_name": "$ConsoleFont",
                "swf_path": "",
                "font_name": "",
                "weight": "Normal",
                "category": "console",
                "flag": "require",
            },
            {
                "map_name": "$EveryFont",
                "swf_path": "",
                "font_name": "",
                "weight": "Normal",
                "category": "every",
                "flag": "option",
            },
        ],
    }


def _use_test_template(tmp_path, monkeypatch):
    template = tmp_path / "template.yml"
    template.write_text(yaml.dump(_template_data()), encoding="utf-8")
    monkeypatch.setattr(preset_mod, "TEMPLATE_PRESET_FILE", template)
    return template


def test_init_loads_template_when_missing(tmp_path, monkeypatch):
    _use_test_template(tmp_path, monkeypatch)

    p = Preset(tmp_path / "nonexistent.yml")
    assert p.data["validnamechars"] == "DEFAULT_CHARS"
    assert len(p.data["mappings"]) == 2


def test_load_applies_migration_and_marks_migrated(tmp_path, monkeypatch):
    _use_test_template(tmp_path, monkeypatch)

    preset_file = tmp_path / "preset.yml"
    preset_file.write_text(
        yaml.dump(
            {
                "swf_dir": "SWF_DIR",
                "output_dir": "OUT_DIR",
                "fontlibs": ["legacy"],
                "valid_name_chars": "ABC",
                "mappings": [{"map_name": "$ConsoleFont", "font_name": "F1"}],
            }
        ),
        encoding="utf-8",
    )

    p = Preset(preset_file)

    assert p.migrated is True
    assert hasattr(p, "swf_dir") and p.swf_dir == "SWF_DIR"
    assert hasattr(p, "output_dir") and p.output_dir == "OUT_DIR"
    assert hasattr(p, "fontlibs") and p.fontlibs == ["legacy"]
    assert p.data["validnamechars"] == "ABC"
    assert p.get_mapping_swf_path("$ConsoleFont") == ""
    assert p.get_mapping_font_name("$ConsoleFont") == "F1"


def test_normalize_mappings_converts_base_group_adds_swf_path_and_dedupes(
    tmp_path, monkeypatch
):
    _use_test_template(tmp_path, monkeypatch)

    preset_file = tmp_path / "preset.yml"
    preset_file.write_text(
        yaml.dump(
            {
                "validnamechars": "XYZ",
                "mappings": [
                    {
                        "map_name": "$ConsoleFont",
                        "base_group": "console",
                        "font_name": "F1",
                    },
                    {
                        "map_name": "$ConsoleFont",
                        "font_name": "F_DUPLICATED",
                    },
                    {
                        "map_name": "$CustomMap",
                        "font_name": "CF",
                        "weight": "Bold",
                        "category": "custom",
                        "flag": "option",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    p = Preset(preset_file)

    names = p.get_mapping_map_names()
    assert names.count("$ConsoleFont") == 1
    assert "$CustomMap" in names

    assert p.get_mapping_category("$ConsoleFont") == "console"
    assert p.get_mapping_swf_path("$ConsoleFont") == ""
    assert p.get_mapping_weight("$CustomMap") == "Bold"


def test_mapping_getters_and_setters(tmp_path, monkeypatch):
    _use_test_template(tmp_path, monkeypatch)

    preset_file = tmp_path / "preset.yml"
    preset_file.write_text(
        yaml.dump(
            {
                "validnamechars": "C",
                "mappings": [
                    {
                        "map_name": "$ConsoleFont",
                        "swf_path": "font/a.swf",
                        "font_name": "A",
                        "weight": "Normal",
                        "category": "console",
                        "flag": "require",
                    },
                    {
                        "map_name": "$EveryFont",
                        "swf_path": "font/a.swf",
                        "font_name": "B",
                        "weight": "Bold",
                        "category": "every",
                        "flag": "option",
                    },
                    {
                        "map_name": "$Custom",
                        "swf_path": "font/c.swf",
                        "font_name": "C",
                        "weight": "Normal",
                        "category": "custom",
                        "flag": "option",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    p = Preset(preset_file)

    assert p.get_mapping_map_names() == ["$ConsoleFont", "$EveryFont", "$Custom"]
    assert p.get_mapping_map_names_by_flag("require") == ["$ConsoleFont"]
    assert p.get_mapping_font_names_by_category("every") == ["B"]
    assert p.get_mapping_swf_paths() == ["font/a.swf", "font/c.swf"]

    assert p.get_mapping_swf_path("$ConsoleFont") == "font/a.swf"
    assert p.get_mapping_font_name("$EveryFont") == "B"
    assert p.get_mapping_category("$Custom") == "custom"
    assert p.get_mapping_weight("$EveryFont") == "Bold"
    assert p.get_mapping_flag("$ConsoleFont") == "require"

    p.set_mapping_font_name("$EveryFont", "B2")
    p.set_mapping_swf_path("$EveryFont", "font/b2.swf")
    p.update_mapping("$Custom", "C2", "font/c2.swf")

    assert p.get_mapping_font_name("$EveryFont") == "B2"
    assert p.get_mapping_swf_path("$EveryFont") == "font/b2.swf"
    assert p.get_mapping_font_name("$Custom") == "C2"
    assert p.get_mapping_swf_path("$Custom") == "font/c2.swf"


def test_property_setters_and_save(tmp_path, monkeypatch):
    _use_test_template(tmp_path, monkeypatch)

    preset_file = tmp_path / "preset.yml"
    preset_file.write_text(yaml.dump(_template_data()), encoding="utf-8")

    p = Preset(preset_file)
    p.mappings = [
        {
            "map_name": "$X",
            "swf_path": "x.swf",
            "font_name": "X",
            "weight": "Normal",
            "category": "custom",
            "flag": "option",
        }
    ]
    p.validnamechars = "NEW_CHARS"
    p.save()

    loaded = yaml.safe_load(preset_file.read_text(encoding="utf-8"))
    assert loaded["mappings"][0]["map_name"] == "$X"
    assert loaded["mappings"][0]["swf_path"] == "x.swf"
    assert loaded["validnamechars"] == "NEW_CHARS"

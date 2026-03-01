from src.modules import find_preview_image as target


def test_priority_1_font_specific_wins(tmp_path):
    swf_path = tmp_path / "apricot_book.swf"
    swf_path.touch()

    font_specific = tmp_path / "apricot_book_Apricot_Font.png"
    swf_same_name = tmp_path / "apricot_book.png"
    font_specific.touch()
    swf_same_name.touch()

    found = target.find_preview_image(swf_path, font_name="Apricot Font")
    assert found == font_specific


def test_priority_1_supports_space_in_sample_filename(tmp_path):
    swf_path = tmp_path / "apricot_book.swf"
    swf_path.touch()

    font_specific_with_space = tmp_path / "apricot_book_Apricot Font.png"
    font_specific_with_space.touch()

    found = target.find_preview_image(swf_path, font_name="Apricot Font")
    assert found == font_specific_with_space


def test_priority_2_swf_same_name(tmp_path):
    swf_path = tmp_path / "cinecaption_every.swf"
    swf_path.touch()

    swf_same_name = tmp_path / "cinecaption_every.png"
    swf_same_name.touch()

    found = target.find_preview_image(swf_path)
    assert found == swf_same_name


def test_priority_3_parent_folder_name(tmp_path):
    parent = tmp_path / "apricot"
    parent.mkdir()
    swf_path = parent / "fonts_apricot.swf"
    swf_path.touch()

    folder_img = parent / "apricot.png"
    folder_img.touch()

    found = target.find_preview_image(swf_path)
    assert found == folder_img


def test_priority_4_keyword_match(monkeypatch, tmp_path):
    swf_path = tmp_path / "fonts_test.swf"
    swf_path.touch()

    keyword_img = tmp_path / "my_preview_image.webp"
    keyword_img.touch()

    monkeypatch.setattr(target, "SAMPLE_IMG_EXT", [".webp"])
    monkeypatch.setattr(
        target, "SAMPLE_IMG_NAME", ["sample", "preview", "preview_image"]
    )

    found = target.find_preview_image(swf_path)
    assert found == keyword_img


def test_return_none_when_no_image(tmp_path):
    swf_path = tmp_path / "fonts_none.swf"
    swf_path.touch()

    found = target.find_preview_image(swf_path)
    assert found is None

from pathlib import Path

from src.const import SAMPLE_IMG_EXT, SAMPLE_IMG_NAME
from src.utils.dprint import dprint


def find_preview_image(
    swf_path: Path, font_name: str = "", debug: bool = False
) -> Path | None:
    """
    SWFに関連するプレビュー画像を優先順位に従って探索する。
    """
    # 探索対象の拡張子（定数から取得、大文字小文字を区別しないように。webp/bmp/gif/png/jpgなど）
    # SAMPLE_IMG_EXT = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"] と想定

    parent_dir = swf_path.parent
    swf_stem = swf_path.byte_stem if hasattr(swf_path, "byte_stem") else swf_path.stem

    # --- 優先順位 1: 最も具体的な一致 (SWF名 + フォント名) ---
    # 例: apricot_book.swf + "ApricotFont" -> apricot_book_ApricotFont.png
    if font_name:
        # 既存運用との互換のため、
        # 1) 生のfont_name（空白含む）
        # 2) 非英数字を"_"に置換した安全名
        # の両方を探索する。
        raw_font_name = font_name.strip()
        safe_font_name = "".join(c if c.isalnum() else "_" for c in raw_font_name)
        candidate_names = []
        for name in (raw_font_name, safe_font_name):
            if name and name not in candidate_names:
                candidate_names.append(name)

        for ext in SAMPLE_IMG_EXT:
            for candidate in candidate_names:
                target = parent_dir / f"{swf_stem}_{candidate}{ext}"
                if target.exists():
                    dprint(f"SWF名+フォント名一致を確認: {target}", debug)
                    return target

    # --- 優先順位 2: SWFファイル名と同一 ---
    # 例: apricot_book.swf -> apricot_book.png
    for ext in SAMPLE_IMG_EXT:
        img = swf_path.with_suffix(ext)
        if img.exists():
            dprint(f"SWFファイル名と一致する画像を発見: {img}", debug)
            return img

    # --- 優先順位 3: 親フォルダ名と一致 ---
    # 例: fonts/Apricot/Apricot.swf において、親の Apricot.png を探す
    folder_name = parent_dir.name
    for ext in SAMPLE_IMG_EXT:
        folder_img = parent_dir / f"{folder_name}{ext}"
        if folder_img.exists():
            dprint(f"親フォルダ名と一致する画像を発見: {folder_img}", debug)
            return folder_img

    # --- 優先順位 4: 特定のキーワードを含む画像 (sample, previewなど) ---
    # SAMPLE_IMG_NAME = ["sample", "preview", "preview_image"] と想定
    for sname in SAMPLE_IMG_NAME:
        # 大文字小文字を無視して glob
        for img in parent_dir.iterdir():
            if img.suffix.lower() in SAMPLE_IMG_EXT:
                if sname.lower() in img.name.lower():
                    dprint(
                        f"フォルダ内にキーワード '{sname}' を含む画像を発見: {img}",
                        debug,
                    )
                    return img

    return None

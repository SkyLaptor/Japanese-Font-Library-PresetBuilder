from pathlib import Path

from src.const import SAMPLE_IMG_EXT, SAMPLE_IMG_NAME
from src.utils.dprint import dprint


def find_preview_image(swf_path: Path, debug: bool = False) -> Path | None:
    # 1. ファイル名一致: apricot_book.swf -> apricot_book.png
    for ext in SAMPLE_IMG_EXT:
        img = swf_path.with_suffix(ext)
        if img.exists():
            dprint(f"SWFファイル名と一致する画像を発見: {img}", debug)
            return img

    # 2. フォルダ内に「sample」や「preview」という名前の画像
    # 3の「フォルダ単位」も兼ねる（そのフォルダの代表画像）
    for sname in SAMPLE_IMG_NAME:
        # sample*.png や preview*.jpg などを一気に探す
        for ext in SAMPLE_IMG_EXT:
            # glob("sample*.png") のようなイメージ
            # もしフォルダ内の全画像から部分一致で探したいなら "*" + sname + "*" + ext
            for img in swf_path.parent.glob(f"*{sname}*{ext}"):
                dprint(f"フォルダ内にサンプル名と一致する画像を発見: {img}", debug)
                return img

    return None

from pathlib import Path
from typing import Dict, List

from modules.generator import preset_generator
from modules.swf_parser import swf_parser


class MainController:
    def __init__(self, settings, preset, cache):
        self.settings = settings
        self.preset = preset
        self.cache = cache

    def scan_swf_directory(self, swf_dir_path: Path, debug: bool = False) -> List[Dict]:
        """スキャンしてフォント名一覧を返す。キャッシュは更新する。

        Returns list of dicts: {"font_name": str, "swf_path": Path}
        """
        font_names_list = []

        for swf_path in swf_dir_path.rglob("*.swf"):
            font_names = swf_parser(
                swf_path=swf_path, cache=self.cache.data, debug=debug
            )
            if font_names:
                try:
                    # cache has `update` method that records relative path and font names
                    self.cache.update(
                        swf_path=swf_path, font_names=font_names, swf_dir=swf_dir_path
                    )
                except Exception:
                    # if cache API differs, ignore to avoid crashing UI
                    pass
                for font_name in font_names:
                    font_names_list.append(
                        {"font_name": font_name, "swf_path": swf_path}
                    )

        return sorted(font_names_list)

    def validate_required_mappings(self) -> list:
        """必須項目チェック。未設定の必須マップ名のリストを返す"""
        missing = []
        for m in self.preset.mappings:
            if m.get("flag") == "require" and (
                not m.get("font_name") or m.get("font_name") == ""
            ):
                missing.append(m.get("map_name"))
        return missing

    def find_missing_fonts(self, available_font_names: set) -> list:
        """現在のスキャン結果に存在しない設定済みフォントを返す"""
        not_found = []
        for m in self.preset.mappings:
            f_name = m.get("font_name")
            if f_name and f_name not in available_font_names:
                not_found.append((m.get("map_name"), f_name))
        return not_found

    def generate_preset(self, output_dir: Path):
        """プリセットを指定フォルダに出力するコア処理。

        - 保存先設定を更新してプリセットを保存
        - `preset_generator` を呼んで出力ファイルパスを返す
        """
        # 更新
        self.preset.output_dir = Path(output_dir)
        self.preset.save()

        # 生成処理（IOや重い処理を含む）
        out_file = preset_generator(self.preset, self.cache.data)
        return out_file

    def save_preset(self):
        """プリセット保存のコア処理（例外が起きたら呼び出し側でハンドル）"""
        self.preset.save()

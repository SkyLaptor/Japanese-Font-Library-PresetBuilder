from pathlib import Path

import yaml

from src.const import (
    ENCODE,
    TEMPLATE_PRESET_FILE,
)


class Preset:
    def __init__(self, preset_path: Path):
        self.preset_path = preset_path
        self.load()
        # 読み込んだ結果、中身が空っぽ（None または {}）だったらテンプレートを読み込んで初期化する
        if not self.data:
            print(
                f"プリセットファイル {self.preset_path} が空または存在しないため、テンプレートを読み込みます。"
            )
            with open(TEMPLATE_PRESET_FILE, "r", encoding=ENCODE) as f:
                self.data = yaml.safe_load(f) or {}
            self.save()

    def load(self):
        """YAMLファイルからプリセットを読み込み、足りない項目はテンプレートで補完する"""
        # テンプレートを「ベース」として読み込む
        try:
            with open(TEMPLATE_PRESET_FILE, "r", encoding=ENCODE) as f:
                template_data = yaml.safe_load(f) or {}
        except Exception as e:
            template_data = {}  # テンプレート読み込み失敗時の保険
            print(f"テンプレートの読み込みに失敗しました: {e}")

        # プリセットファイルを読み込む
        loaded_data = {}
        if self.preset_path.exists():
            try:
                with open(self.preset_path, "r", encoding=ENCODE) as f:
                    loaded_data = yaml.safe_load(f)
                    if loaded_data:
                        # 1.0.0rc2以前のプリセットファイルに対するアップデート処理
                        if "swf_dir" in loaded_data:
                            print(
                                f"swf_dirが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded_data['swf_dir']}"
                            )
                            self.swf_dir = loaded_data.pop("swf_dir")
                        if "output_dir" in loaded_data:
                            print(
                                f"output_dirが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded_data["output_dir"]}"
                            )
                            self.output_dir = loaded_data.pop("output_dir")
                        if "fontlibs" in loaded_data:
                            print(
                                f"fontlibsが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded_data["fontlibs"]}"
                            )
                            self.fontlibs = loaded_data.pop("fontlibs")
                        if "valid_name_chars" in loaded_data:
                            print(
                                "valid_name_charsが存在しています。取り出してvalidnamecharsで入れ直します。"
                            )
                            loaded_data["validnamechars"] = loaded_data.pop(
                                "valid_name_chars"
                            )
                        if "mappings" in loaded_data:
                            for map in loaded_data["mappings"]:
                                if "swf_path" not in map:
                                    print(
                                        f"swf_pathが存在しません。空で追加します。必要に応じて値を投入して下さい。: {map['font_name']}"
                                    )
                                    map["swf_path"] = ""
            except Exception as e:
                print(f"プリセットの読み込みに失敗しました: {e}")

        # テンプレートをロードしたデータで上書きして補完
        template_data.update(loaded_data)
        self.data = template_data  # 最終的なデータをセット

    def save(self):
        """現在のプリセットをYAMLファイルに保存する"""
        try:
            # 親ディレクトリがなければ作成
            self.preset_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.preset_path, "w", encoding=ENCODE) as f:
                yaml.dump(self.data, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            print(f"プリセットの保存に失敗しました: {e}")

    @property
    def mappings(self):
        return self.data["mappings"]

    @mappings.setter
    def mappings(self, value: list):
        self.data["mappings"] = value

    def get_mapping_swf_path(self, map_name: str) -> str:
        """指定されたマップ名に対応する現在のSWFフォントパスを取得する"""
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                return m.get("swf_path", "")
        return ""

    def get_mapping_font_name(self, map_name: str) -> str:
        """指定されたマップ名に対応する現在のフォント名を取得する"""
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                return m.get("font_name", "")
        return ""

    @property
    def validnamechars(self):
        return self.data["validnamechars"]

    @validnamechars.setter
    def validnamechars(self, value: str):
        self.data["validnamechars"] = value

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
                    loaded_data = yaml.safe_load(f) or {}
                # アップデート処理をインスタンスメソッドへ切り出すため、一時的に保持して呼び出す
                self._loaded_data = loaded_data
                if self._loaded_data:
                    self.migrate_legacy_data()
                loaded_data = self._loaded_data
                self.data = loaded_data  # マイグレート後のデータをセット
            except Exception as e:
                print(f"プリセットの読み込みに失敗しました: {e}")

        # テンプレートをロードしたデータで上書きして補完
        template_data.update(loaded_data)
        self.data = template_data  # 最終的なデータをセット

    def _normalize_mappings(self, loaded: dict, template_data: dict):
        """mappings をテンプレート準拠で補完・正規化する。"""
        if "mappings" not in loaded or not isinstance(loaded.get("mappings"), list):
            return

        template_mappings = template_data.get("mappings", []) or []
        template_by_name = {
            t.get("map_name"): t for t in template_mappings if isinstance(t, dict)
        }

        normalized = []
        for m in loaded["mappings"]:
            if not isinstance(m, dict):
                continue

            # 旧キー互換: base_group -> category
            if "base_group" in m and "category" not in m:
                m["category"] = m.pop("base_group")

            map_name = m.get("map_name")
            if map_name in template_by_name:
                merged = dict(template_by_name[map_name])
                merged.update(m)
            else:
                merged = {
                    "map_name": map_name or "",
                    "swf_path": "",
                    "font_name": "",
                    "weight": "Normal",
                    "category": "custom",
                    "flag": "option",
                }
                merged.update(m)

            # 1.0.0rc2+ は swf_path 必須
            if "swf_path" not in merged:
                print(
                    f"swf_pathが存在しません。空で追加します。必要に応じて値を投入して下さい。: {merged.get('font_name', '')}"
                )
                merged["swf_path"] = ""

            normalized.append(merged)

        loaded["mappings"] = normalized

    def migrate_legacy_data(self):
        """バージョンアップに伴う古いプリセットデータのマイグレーション処理"""
        loaded = getattr(self, "_loaded_data", {}) or {}

        try:
            with open(TEMPLATE_PRESET_FILE, "r", encoding=ENCODE) as f:
                template_data = yaml.safe_load(f) or {}
        except Exception:
            template_data = {}
        # 1.0.0rc2以降はsettings.ymlに移行
        if "swf_dir" in loaded:
            print(
                f"swf_dirが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded['swf_dir']}"
            )
            self.swf_dir = loaded.pop("swf_dir")
        # 1.0.0rc2以降はsettings.ymlに移行
        if "output_dir" in loaded:
            print(
                f"output_dirが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded['output_dir']}"
            )
            self.output_dir = loaded.pop("output_dir")
        # 1.0.0rc2以降は不要。そもそも使用されていなかったはず。
        if "fontlibs" in loaded:
            print(
                f"fontlibsが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded['fontlibs']}"
            )
            self.fontlibs = loaded.pop("fontlibs")
        # 1.0.0rc2以降は名前を変更してcategoryに移行
        if "base_group" in loaded:
            print("base_groupが存在しています。取り出してcategoryで入れ直します。")
            loaded["category"] = loaded.pop("base_group")
        # 1.0.0rc2以降は名前を変更してvalidnamecharsに移行
        if "valid_name_chars" in loaded:
            print(
                "valid_name_charsが存在しています。取り出してvalidnamecharsで入れ直します。"
            )
            loaded["validnamechars"] = loaded.pop("valid_name_chars")
        # mappings はテンプレート準拠で項目補完しつつ正規化する
        self._normalize_mappings(loaded, template_data)

        # 更新したデータを戻しておく
        self._loaded_data = loaded

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

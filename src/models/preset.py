from pathlib import Path

import yaml

from src.const import (
    ENCODE,
    TEMPLATE_PRESET_FILE,
)
from utils.dprint import dprint


class Preset:
    def __init__(self, preset_path: Path, debug: bool = False):
        self.preset_path = preset_path
        self.debug = debug
        self.data = {}
        self.load()
        # 読み込んだ結果、中身が空っぽ（None または {}）だったらテンプレートを読み込んで初期化する
        if not self.data:
            dprint(
                f"プリセットファイル {self.preset_path} が空または存在しないため、テンプレートを読み込みます。",
                self.debug,
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

        seen_names = set()  # 通過した名前をメモする
        unique_list = []  # 綺麗なリストを作る

        template_mappings = template_data.get("mappings", []) or []
        template_by_name = {
            t.get("map_name"): t for t in template_mappings if isinstance(t, dict)
        }

        for m in loaded["mappings"]:
            if not isinstance(m, dict):
                continue

            # 旧キー互換: base_group -> category
            if "base_group" in m and "category" not in m:
                dprint(
                    "base_groupが存在しています。取り出してcategoryで入れ直します。",
                    self.debug,
                )
                m["category"] = m.pop("base_group")

            map_name = m.get("map_name")

            # 重複したmap_nameはスキップする（最初の1つだけ採用）
            if map_name in seen_names:
                dprint(f"重複した map_name を検出、無視します: {map_name}", self.debug)
                continue
            seen_names.add(map_name)  # 初めて見る名前ならメモして通過許可

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

            unique_list.append(merged)

        loaded["mappings"] = unique_list

    def migrate_legacy_data(self):
        """バージョンアップに伴う古いプリセットデータのマイグレーション処理"""
        migrated = False
        loaded = getattr(self, "_loaded_data", {}) or {}

        try:
            with open(TEMPLATE_PRESET_FILE, "r", encoding=ENCODE) as f:
                template_data = yaml.safe_load(f) or {}
        except Exception:
            template_data = {}
        # 1.0.0rc2以降はsettings.ymlに移行
        if "swf_dir" in loaded:
            dprint(
                f"swf_dirが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded['swf_dir']}",
                self.debug,
            )
            self.swf_dir = loaded.pop("swf_dir")
            migrated = True
        # 1.0.0rc2以降はsettings.ymlに移行
        if "output_dir" in loaded:
            dprint(
                f"output_dirが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded['output_dir']}",
                self.debug,
            )
            self.output_dir = loaded.pop("output_dir")
            migrated = True
        # 1.0.0rc2以降は不要。そもそも使用されていなかったはず。
        if "fontlibs" in loaded:
            dprint(
                f"fontlibsが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded['fontlibs']}",
                self.debug,
            )
            self.fontlibs = loaded.pop("fontlibs")
            migrated = True
        # 1.0.0rc2以降は名前を変更してcategoryに移行
        if "base_group" in loaded:
            dprint(
                "base_groupが存在しています。取り出してcategoryで入れ直します。",
                self.debug,
            )
            loaded["category"] = loaded.pop("base_group")
            migrated = True
        # 1.0.0rc2以降は名前を変更してvalidnamecharsに移行
        if "valid_name_chars" in loaded:
            dprint(
                "valid_name_charsが存在しています。取り出してvalidnamecharsで入れ直します。",
                self.debug,
            )
            loaded["validnamechars"] = loaded.pop("valid_name_chars")
            migrated = True
        # mappings はテンプレート準拠で項目補完しつつ正規化する
        self._normalize_mappings(loaded, template_data)
        # 更新したデータを戻しておく
        self._loaded_data = loaded
        self.migrated = migrated

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

    def get_mapping_map_names(self) -> list:
        """mappings 内の全 map_name を取得する"""
        return [
            m.get("map_name", "")
            for m in self.data.get("mappings", [])
            if isinstance(m, dict)
        ]

    def get_mapping_map_names_by_flag(self, flag: str) -> list:
        """
        mappings 内の flag が指定された値の map_name を取得する

        使用例:
        * requireフラグが経っているマッピングにきちんと font_name や swf_path が入っているかチェックしたいときなど
        """
        return [
            m.get("map_name", "")
            for m in self.data.get("mappings", [])
            if isinstance(m, dict) and m.get("flag") == flag
        ]

    def get_mapping_font_names_by_category(self, category: str) -> list:
        """指定した category に対応する font_name を取得する"""
        return [
            m.get("font_name", "")
            for m in self.data.get("mappings", [])
            if isinstance(m, dict) and m.get("category") == category
        ]

    def get_mapping_swf_paths(self) -> list:
        """
        mappings 内の全 swf_path を重複を排除したリストで返す

        swf_path はSWFディレクトリからの相対パスで返す（例: "font1/font1_every.swf"）。存在しない場合は空文字列を返す。

        使用例:
        * fontconfig.txt書き出し時に、fontlibセクションに必要なSWFファイルのパスを収集するためなど
        """
        paths = {
            m.get("swf_path", "")
            for m in self.data.get("mappings", [])
            if isinstance(m, dict) and m.get("swf_path")
        }
        # ソートしてリストで返す（安定した順序で扱いたい場合などに便利）
        return sorted(list(paths))

    def get_mapping_swf_path(self, map_name: str) -> str:
        """
        指定された map_name に対応する swf_path を取得する

        swf_path はSWFディレクトリからの相対パスで返す（例: "font1/font1_every.swf"）。存在しない場合は空文字列を返す。
        """
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                return m.get("swf_path", "")
        return ""

    def set_mapping_swf_path(self, map_name: str, swf_path: str):
        """
        指定された map_name に対応する swf_path を設定する

        swf_path はSWFディレクトリからの相対パスで渡すこと（例: "font1/font1_every.swf"）。
        """
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                m["swf_path"] = swf_path
                return

    def get_mapping_font_name(self, map_name: str) -> str:
        """指定された map_name に対応する font_name を取得する"""
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                return m.get("font_name", "")
        return ""

    def set_mapping_font_name(self, map_name: str, font_name: str):
        """指定された map_name に対応する font_name を設定する"""
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                m["font_name"] = font_name
                return

    def update_mapping(self, map_name: str, font_name: str, swf_path: str):
        """
        指定された map_name に対する font_name, swf_path をまとめて設定する

        swf_path はSWFディレクトリからの相対パスで渡すこと（例: "font1/font1_every.swf"）。
        """
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                m["font_name"] = font_name
                m["swf_path"] = swf_path
                return

    def get_mapping_category(self, map_name: str) -> str:
        """指定された map_name に対応する category を取得する"""
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                return m.get("category", "")
        return ""

    def get_mapping_weight(self, map_name: str) -> str:
        """指定された map_name に対応する weight を取得する"""
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                return m.get("weight", "")
        return ""

    def get_mapping_flag(self, map_name: str) -> str:
        """指定された map_name に対応する flag を取得する"""
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                return m.get("flag", "")
        return ""

    @property
    def validnamechars(self):
        return self.data["validnamechars"]

    @validnamechars.setter
    def validnamechars(self, value: str):
        self.data["validnamechars"] = value

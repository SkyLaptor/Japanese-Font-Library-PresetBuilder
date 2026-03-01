from pathlib import Path

import yaml

from const import ENCODE, TEMPLATE_SETTINGS_FILE
from utils.dprint import dprint


class Settings:
    def __init__(self, settings_path: Path, debug: bool = False):
        self.settings_path = settings_path
        self.debug = debug
        settings_exists = self.settings_path.exists()
        self.load()
        if not settings_exists:
            dprint("settings.yml が存在しないため、初期値を保存します。", self.debug)
            self.save()
        # 読み込んだ結果、中身が空っぽ（None または {}）だったらテンプレートを読み込んで初期化する
        if not self.data:
            dprint(
                "システム設定が空または存在しないため、テンプレートを読み込みます。",
                self.debug,
            )
            with open(TEMPLATE_SETTINGS_FILE, "r", encoding=ENCODE) as f:
                self.data = yaml.safe_load(f) or {}
            self.save()

    def load(self):
        """YAMLファイルからシステム設定を読み込み、足りない項目はテンプレートで補完する"""
        # テンプレートを「ベース」として読み込む
        try:
            with open(TEMPLATE_SETTINGS_FILE, "r", encoding=ENCODE) as f:
                template_data = yaml.safe_load(f) or {}
        except Exception as e:
            template_data = {}  # テンプレート読み込み失敗時の保険
            print(f"テンプレートの読み込みに失敗しました: {e}")

        # システム設定ファイルを読み込む
        loaded_data = {}
        if self.settings_path.exists():
            try:
                with open(self.settings_path, "r", encoding=ENCODE) as f:
                    loaded_data = yaml.safe_load(f) or {}
                # マイグレート処理を実行
                self._loaded_data = loaded_data
                if self._loaded_data:
                    self.migrate_legacy_data()
                loaded_data = self._loaded_data
                self.data = loaded_data  # マイグレート後のデータをセット
            except Exception as e:
                print(f"システム設定の読み込みに失敗しました: {e}")

        # テンプレートをロードしたデータで上書きして補完
        template_data.update(loaded_data)
        self.data = template_data  # 最終的なデータをセット

    def migrate_legacy_data(self):
        """バージョンアップに伴う古いシステム設定データのマイグレーション処理"""
        migrated = False
        loaded = getattr(self, "_loaded_data", {}) or {}
        # 1.0.0rc2以降は不要。そもそも使用されていなかったはず。
        if "weight_type" in loaded:
            dprint(
                f"weight_typeが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded['weight_type']}",
                self.debug,
            )
            self.weight_type = loaded.pop("weight_type")
            migrated = True
        # 1.0.0rc2以前はpreset.ymlに保持していたが、1.0.0rc2以降はsettings.ymlに移行
        if "swf_dir" not in loaded:
            dprint(
                "swf_dirが存在しません。空で追加します。必要に応じて値を投入して下さい。",
                self.debug,
            )
            loaded["swf_dir"] = ""
            migrated = True
        # 1.0.0rc2以前はpreset.ymlに保持していたが、1.0.0rc2以降はsettings.ymlに移行
        if "output_dir" not in loaded:
            dprint(
                "output_dirが存在しません。空で追加します。必要に応じて値を投入して下さい。",
                self.debug,
            )
            loaded["output_dir"] = ""
            migrated = True
        # 1.0.0rc2以降は名前を変更してlast_presetに移行
        if "last_preset_name" in loaded:
            dprint(
                "last_preset_nameが存在しています。取り出してlast_presetで入れ直します。",
                self.debug,
            )
            loaded["last_preset"] = loaded.pop("last_preset_name")
            migrated = True
        # 更新したデータを戻しておく
        self._loaded_data = loaded
        self.migrated = migrated

    def save(self):
        """現在のシステム設定をYAMLファイルに保存する"""
        try:
            with open(self.settings_path, "w", encoding=ENCODE) as f:
                yaml.dump(self.data, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            print(f"システム設定ファイルの保存に失敗しました: {e}")

    @property
    def last_preset(self):
        """last_preset をプリセットディレクトリ(preset)からの相対パスで返す

        "preset/example.yml" の場合は "example.yml" 。存在しない場合は空文字列を返す。
        """
        return self.data.get("last_preset", "")

    @last_preset.setter
    def last_preset(self, value):
        """last_preset を設定する

        last_preset はプリセットディレクトリ(preset)からの相対パスで渡すこと。
        例: "preset/example.yml" の場合は "example.yml" 。
        """
        self.data["last_preset"] = value

    @property
    def swf_dir(self):
        """swf_dir を返す

        swf_dir は絶対パスである（例: "C:/path/to/swf"）。存在しない場合は空文字列を返す。
        """
        return self.data.get("swf_dir", "")

    @swf_dir.setter
    def swf_dir(self, value):
        """swf_dir を設定する

        swf_dir は絶対パスで渡すこと（例: "C:/path/to/swf"）。"""
        self.data["swf_dir"] = value

    @property
    def output_dir(self):
        """output_dir を返す

        output_dir は絶対パスである（例: "C:/path/to/output"）。存在しない場合は空文字列を返す。
        """
        return self.data.get("output_dir", "")

    @output_dir.setter
    def output_dir(self, value):
        """output_dir を設定する

        output_dir は絶対パスで渡すこと（例: "C:/path/to/output"）。"""
        self.data["output_dir"] = value

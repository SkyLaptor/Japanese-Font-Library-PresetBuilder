import copy
from pathlib import Path

import yaml

from const import DEFAULT_SETTINGS, ENCODE


class Settings:
    def __init__(self, settings_path: Path):
        self.settigs_path = settings_path
        # システム設定ファイルが存在しない場合はデフォルト値を使用する。
        self.settings = None
        if not settings_path.exists():
            print(
                "システム設定ファイルが存在しないため、デフォルト値でシステム設定ファイルを生成します。"
            )
            self.settings = copy.deepcopy(DEFAULT_SETTINGS)
            self.save()
        else:
            with open(self.settigs_path, "r", encoding=ENCODE) as f:
                self.settings = yaml.safe_load(f)

    def load(self):
        """YAMLファイルから設定を読み込む"""
        if self.settigs_path.exists():
            try:
                with open(self.settigs_path, "r", encoding=ENCODE) as f:
                    loaded_data = yaml.safe_load(f)
                    if loaded_data:
                        self.settings.update(loaded_data)
            except Exception as e:
                print(f"システム設定ファイルの読み込みに失敗しました: {e}")

    def save(self):
        """現在の設定をYAMLファイルに保存する"""
        try:
            with open(self.settigs_path, "w", encoding=ENCODE) as f:
                yaml.dump(self.settings, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            print(f"システム設定ファイルの保存に失敗しました: {e}")

    @property
    def ffdec_cli(self):
        return Path(self.settings["ffdec_cli"])

    @property
    def last_preset_path(self):
        return self.settings.get("last_preset_path")

    @last_preset_path.setter
    def last_preset_path(self, value):
        self.settings["last_preset_path"] = value

    @property
    def weight_type(self):
        return self.settings["weight_type"]

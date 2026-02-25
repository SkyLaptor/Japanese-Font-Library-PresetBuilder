from pathlib import Path

import yaml

from const import ENCODE, TEMPLATE_SETTINGS_FILE


class Settings:
    def __init__(self, settings_path: Path):
        self.settings_path = settings_path
        self.load()
        # 読み込んだ結果、中身が空っぽ（None または {}）だったらテンプレートを読み込んで初期化する
        if not self.data:
            print("システム設定が空または存在しないため、テンプレートを読み込みます。")
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
                    loaded_data = (
                        yaml.safe_load(f) or {}
                    )  # ファイルが空の場合は空の辞書を使用
                    if loaded_data:
                        # 1.0.0rc2以前のシステム設定ファイルに対するアップデート処理
                        if "weight_type" in loaded_data:
                            print(
                                f"weight_typeが存在しています。取り出して同名で一時保管します。必要に応じて保存して下さい。: {loaded_data['weight_type']}"
                            )
                            self.weight_type = loaded_data.pop("weight_type")
                        if "swf_dir" not in loaded_data:
                            print(
                                "swf_dirが存在しません。空で追加します。必要に応じて値を投入して下さい。"
                            )
                            loaded_data["swf_dir"] = ""
                        if "output_dir" not in loaded_data:
                            print(
                                "output_dirが存在しません。空で追加します。必要に応じて値を投入して下さい。"
                            )
                            loaded_data["output_dir"] = ""
                        if "last_preset_name" in loaded_data:
                            print(
                                "last_preset_nameが存在しています。取り出してlast_presetで入れ直します。"
                            )
                            loaded_data["last_preset"] = loaded_data.pop(
                                "last_preset_name"
                            )
            except Exception as e:
                print(f"システム設定の読み込みに失敗しました: {e}")

        # テンプレートをロードしたデータで上書きして補完
        template_data.update(loaded_data)
        self.data = template_data  # 最終的なデータをセット

    def save(self):
        """現在のシステム設定をYAMLファイルに保存する"""
        try:
            with open(self.settings_path, "w", encoding=ENCODE) as f:
                yaml.dump(self.data, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            print(f"システム設定ファイルの保存に失敗しました: {e}")

    @property
    def last_preset(self):
        return self.data.get("last_preset", "")

    @last_preset.setter
    def last_preset(self, value):
        self.data["last_preset"] = value

    @property
    def swf_dir(self):
        return self.data.get("swf_dir", "")

    @swf_dir.setter
    def swf_dir(self, value):
        self.data["swf_dir"] = value

    @property
    def output_dir(self):
        return self.data.get("output_dir", "")

    @output_dir.setter
    def output_dir(self, value):
        self.data["output_dir"] = value

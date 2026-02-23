import copy
from datetime import datetime
from pathlib import Path

import yaml

from src.const import (
    DEFAULT_USER_CONFIG,
    DEFAULT_VALID_NAME_CHARS,
    ENCODE,
    INTERFACE_DIR,
    TIME_FORMAT,
)


class UserConfig:
    def __init__(self, user_config_path: Path):
        self.user_config_path = user_config_path
        # ユーザー設定ファイルが存在しない場合はデフォルト値を使用する。
        self.user_config = None
        if not user_config_path.exists():
            print(
                "ユーザー設定ファイルが存在しないため、デフォルト値でユーザー設定ファイルを生成します。"
            )
            self.user_config = copy.deepcopy(DEFAULT_USER_CONFIG)
            # --- valid_name_chars の初期値設定 ---
            if "valid_name_chars" not in self.user_config:
                self.user_config["valid_name_chars"] = (
                    self.load_default_validnamechars()
                )
            self.save()
        else:
            with open(self.user_config_path, "r", encoding=ENCODE) as f:
                self.user_config = yaml.safe_load(f)

    def load(self):
        """YAMLファイルから設定を読み込む"""
        if self.user_config_path.exists():
            try:
                with open(self.user_config_path, "r", encoding=ENCODE) as f:
                    loaded_data = yaml.safe_load(f)
                    if loaded_data:
                        self.user_config.update(loaded_data)
            except Exception as e:
                print(f"ユーザー設定の読み込みに失敗しました: {e}")

    def save(self):
        """現在の設定をYAMLファイルに保存する"""
        try:
            with open(self.user_config_path, "w", encoding=ENCODE) as f:
                yaml.dump(self.user_config, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            print(f"ユーザー設定の保存に失敗しました: {e}")

    def load_default_validnamechars(self):
        """外部テキストファイルから初期文字セットを読み込む"""
        default_file = DEFAULT_VALID_NAME_CHARS
        if default_file.exists():
            try:
                return (
                    # 改行コードなど制御文字だけ消して読み込み
                    default_file.read_text(encoding=ENCODE)
                    .replace("\n", "")
                    .replace("\r", "")
                    .replace("\t", "")
                )
            except Exception as e:
                print(f"⚠️ 文字セットファイルの読み込みに失敗: {e}")

        # ファイルがない場合のフォールバック（最低限のセット）
        return "$-_0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.,\"' "

    def update_swf_cache(self, swf_path: Path, font_names: list):
        """解析したフォント名をキャッシュに保存/更新する"""
        # 保存時は swf_dir からの相対パスにする（環境移行対策）
        try:
            rel_path = str(swf_path.relative_to(self.swf_dir))
        except ValueError:
            rel_path = str(swf_path)

        mtime = datetime.fromtimestamp(swf_path.stat().st_mtime).strftime(TIME_FORMAT)

        # 既存のキャッシュがあれば更新、なければ追加
        found = False
        for entry in self.user_config["cache"]:
            if entry["swf_path"] == rel_path:
                entry["modified_date"] = mtime
                entry["font_names"] = font_names
                found = True
                break

        if not found:
            self.user_config["cache"].append(
                {
                    "swf_path": rel_path,
                    "modified_date": mtime,
                    "font_names": font_names,
                    "hash": "",  # 将来用
                }
            )

    def get_required_swfs(self):
        """
        現在マッピングされているフォントが必要とするSWFパスのリストを返す。
        """
        selected_fonts = {m["font_name"] for m in self.mappings if m["font_name"]}
        required_swfs = set()

        # --- 1. デフォルト必須分 (fonts_core.swf など) ---
        for lib in self.fontlibs:
            if lib.get("flag") == "require":
                # Pathオブジェクトにして as_posix() でスラッシュに統一
                p = Path(lib["swf_path"])
                required_swfs.add(p.as_posix())

        # マッピングされたフォントがどのキャッシュ（SWF）に属しているか探す
        for font in selected_fonts:
            for entry in self.user_config.get("cache", []):
                if font in entry.get("font_names", []):
                    # SWFパスを fontlib 用の形式で追加
                    # 慣例的にInterfaceフォルダの中に置く。
                    swf_name = Path(entry["swf_path"]).name
                    swf_path = Path(INTERFACE_DIR) / swf_name
                    required_swfs.add(f"{swf_path}")
                    break

        return sorted(list(required_swfs))

    # 便利なゲッター/セッター
    @property
    def swf_dir(self):
        path_str = self.user_config.get("swf_dir", "")
        # 空文字だったら None を返す（または空のPathを返さないようにする）
        if not path_str:
            return None
        return Path(path_str)

    @swf_dir.setter
    def swf_dir(self, value: Path):
        self.user_config["swf_dir"] = str(value)

    @property
    def output_dir(self):
        return Path(self.user_config["output_dir"])

    @output_dir.setter
    def output_dir(self, value: Path):
        self.user_config["output_dir"] = str(value)

    @property
    def fontlibs(self):
        return self.user_config["fontlibs"]

    @fontlibs.setter
    def fontlibs(self, value: list):
        self.user_config["fontlibs"] = value

    @property
    def mappings(self):
        return self.user_config["mappings"]

    @mappings.setter
    def mappings(self, value: list):
        self.user_config["mappings"] = value

    def get_mapping_font(self, map_name: str) -> str:
        """指定されたマップ名に対応する現在のフォント名を取得する"""
        for m in self.user_config["mappings"]:
            if m["map_name"] == map_name:
                return m.get("font_name", "")
        return ""

    @property
    def valid_name_chars(self):
        return self.user_config["valid_name_chars"]

    @valid_name_chars.setter
    def valid_name_chars(self, value: str):
        self.user_config["valid_name_chars"] = value

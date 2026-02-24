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


class Preset:
    def __init__(self, preset_path: Path):
        self.preset_path = preset_path
        # プリセットファイルが存在しない場合はデフォルト値を使用する。
        self.data = None
        if not preset_path.exists():
            print("プリセットファイルが存在しないため、デフォルト値で生成します。")
            self.data = copy.deepcopy(DEFAULT_USER_CONFIG)
            # --- valid_name_chars の初期値設定 ---
            if "valid_name_chars" not in self.data:
                self.data["valid_name_chars"] = self.load_default_validnamechars()
            self.save()
        else:
            with open(self.preset_path, "r", encoding=ENCODE) as f:
                self.data = yaml.safe_load(f)

    def load(self):
        """YAMLファイルから設定を読み込む"""
        if self.preset_path.exists():
            try:
                with open(self.preset_path, "r", encoding=ENCODE) as f:
                    loaded_data = yaml.safe_load(f)
                    if loaded_data:
                        self.data.update(loaded_data)
            except Exception as e:
                print(f"ユーザー設定の読み込みに失敗しました: {e}")

    def save(self):
        """現在の設定をYAMLファイルに保存する"""
        try:
            # 親ディレクトリがなければ作成
            self.preset_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.preset_path, "w", encoding=ENCODE) as f:
                yaml.dump(self.data, f, allow_unicode=True, sort_keys=False)
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
        for entry in self.data["cache"]:
            if entry["swf_path"] == rel_path:
                entry["modified_date"] = mtime
                entry["font_names"] = font_names
                found = True
                break

        if not found:
            self.data["cache"].append(
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
            for entry in self.data.get("cache", []):
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
        path_str = self.data.get("swf_dir", "")
        # 空文字だったら None を返す（または空のPathを返さないようにする）
        if not path_str:
            return None
        return Path(path_str)

    @swf_dir.setter
    def swf_dir(self, value: Path):
        self.data["swf_dir"] = str(value)

    @property
    def output_dir(self):
        return Path(self.data["output_dir"])

    @output_dir.setter
    def output_dir(self, value: Path):
        self.data["output_dir"] = str(value)

    @property
    def fontlibs(self):
        return self.data["fontlibs"]

    @fontlibs.setter
    def fontlibs(self, value: list):
        self.data["fontlibs"] = value

    @property
    def mappings(self):
        return self.data["mappings"]

    @mappings.setter
    def mappings(self, value: list):
        self.data["mappings"] = value

    def get_mapping_font(self, map_name: str) -> str:
        """指定されたマップ名に対応する現在のフォント名を取得する"""
        for m in self.data["mappings"]:
            if m["map_name"] == map_name:
                return m.get("font_name", "")
        return ""

    @property
    def valid_name_chars(self):
        return self.data["valid_name_chars"]

    @valid_name_chars.setter
    def valid_name_chars(self, value: str):
        self.data["valid_name_chars"] = value

from pathlib import Path

# メインウィンドウのタイトル
MAIN_WINDOW_TITLE = "Japanese Font Library - PresetBuilder"

# 日付フォーマット（キャッシュ比較で使用するため取り扱い注意）
TIME_FORMAT = "%Y/%m/%d %H:%M:%S"
# デフォルトのファイル読み書き時のエンコード
ENCODE = "utf-8"
# スカイリムのフォントコンフィグの文字コード(UTF-8)
# OldrimはBOM付UTF-8（utf_8_sig）だが、別にUTF-8でも動作する。
SKYRIM_FONTCONFIG_ENCODE = "utf-8"

# ベースディレクトリ
BASE_DIR = Path(__file__).parent.parent
# データディレクトリ（テンプレート類やキャッシュをここに置いておく。）
DATA_DIR = BASE_DIR / "data"
# プリセットディレクトリ
PRESETS_DIR = BASE_DIR / "preset"

# テンプレートプログラム設定ファイル
TEMPLATE_SETTINGS_FILE = DATA_DIR / "template_settings.yml"
# プログラム設定ファイル
SETTINGS_FILE = BASE_DIR / "settings.yml"
# テンプレートプリセットファイル
TEMPLATE_PRESET_FILE = DATA_DIR / "template_preset.yml"
# キャッシュファイル
CACHE_FILE = DATA_DIR / "cache.yml"

# スカイリムにおける各種ディレクトリ名
# インタフェースディレクトリ名
SKYRIM_INTERFACE_DIR_NAME = "Interface"

# 表示を許可するマッピングカテゴリ
# ymlは任意に書けてしまうためこれで制限する。あと順番もこれで制御する。
ALLOW_MAPPING_CATEGORY = [
    "every",
    "book",
    "handwrite",
    "console",
    "special",
    "mcm",
    "custom",
]

# サンプル画像拡張子
SAMPLE_IMG_EXT = [".png", ".jpg", ".jpeg"]
# サンプル画像ファイル名
SAMPLE_IMG_NAME = ["sample", "preview", "image"]

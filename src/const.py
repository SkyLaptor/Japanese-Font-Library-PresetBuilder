from pathlib import Path

PROGRAM_TITLE = "Japanese Font Library - PresetBuilder"
# ファイル読み書きエンコード
ENCODE = "utf-8"
# スカイリムのフォントコンフィグの文字コード 本来BOM付きらしいが...
FONTCONFIG_ENCODE = "utf-8"
INTERFACE_DIR = Path("Interface")
# 各種ディレクトリ
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
BUILD_DIR = BASE_DIR / "build"
PRESETS_DIR = BASE_DIR / "preset"
# プログラム設定ファイル
SETTINGS_FILE = BASE_DIR / "settings.yml"
# デフォルトのプログラム設定（settings.ymlを消されたりなど、トラブル時以外は普通は使用されない）
DEFAULT_SETTINGS = {
    "last_preset_name": "",
    "weight_type": [
        "Normal",
        "Bold",
        "Roman",  # 普通使わない。
        "Demi",  # 普通使わない。
    ],
}
# 一括設定用
# 入力値の検証とかに使えたらいいな
BASE_GROUP = ["every", "book", "handwrite", "console", "special", "mcm", "custom"]
FLAG_GROUP = ["require", "option"]
# ユーザー設定ファイル
USER_CONFIG_FILE = PRESETS_DIR / "default.yml"
# デフォルトのユーザー設定ファイル（config.yml消されたりなど、トラブル時以外は普通は使用されない）
# ゲームが更新されたらなるべく早めに直しておくこと。取り急ぎ実ファイルを直せばいいけど。
DEFAULT_USER_CONFIG = {
    "swf_dir": "",
    "output_dir": "",
    "fontlibs": [
        # {
        #     "swf_path": r"Interface/fonts_core.swf",
        #     "flag": "require",  # ユーザーが追加した(もしくはプログラム的に追加された)ものであれば "added" 。このフラグを見て、システム的に削除時に警告やブロックしたりしたい。
        # }, 必須のものがある場合は追記
    ],  # ユーザーが追加したSWFはここに {"path": "...", "flag": "added"} と入る
    "mappings": [
        {
            "map_name": "$ConsoleFont",
            "font_name": "",
            "weight": "Normal",  # SETTINGS["weight"] のいずれか。
            "base_group": "console",  # BASE_GROUP のいずれか
            "flag": "require",  # ユーザーが追加したものであれば "added" 。このフラグを見て、システム的に削除時に警告やブロックしたりしたい。
        },
        {
            "map_name": "$StartMenuFont",
            "font_name": "",
            "weight": "Normal",
            "base_group": "every",
            "flag": "require",
        },
        {
            "map_name": "$DialogueFont",
            "font_name": "",
            "weight": "Normal",
            "base_group": "every",
            "flag": "require",
        },
        {
            "map_name": "$EverywhereFont",
            "font_name": "",
            "weight": "Normal",
            "base_group": "every",
            "flag": "require",
        },
        {
            "map_name": "$EverywhereBoldFont",
            "font_name": "",
            "weight": "Normal",
            "base_group": "every",
            "flag": "require",
        },
        {
            "map_name": "$EverywhereMediumFont",
            "font_name": "",
            "weight": "Normal",
            "base_group": "every",
            "flag": "require",
        },
        {
            "map_name": "$CClub_Font",
            "font_name": "",
            "weight": "Normal",
            "base_group": "every",
            "flag": "require",
        },
        {
            "map_name": "$CClub_Font_Bold",
            "font_name": "",
            "weight": "Normal",
            "base_group": "every",
            "flag": "require",
        },
        {
            "map_name": "Times New Roman",
            "font_name": "",
            "weight": "Normal",
            "base_group": "every",
            "flag": "require",
        },
        {
            "map_name": "$CreditsFont",
            "font_name": "",
            "weight": "Normal",
            "base_group": "every",
            "flag": "require",
        },
        {
            "map_name": "$SkyrimBooks",
            "font_name": "",
            "weight": "Normal",
            "base_group": "book",
            "flag": "require",
        },
        {
            "map_name": "$HandwrittenFont",
            "font_name": "",
            "weight": "Normal",
            "base_group": "handwrite",
            "flag": "require",
        },
        {
            "map_name": "$HandwrittenBold",
            "font_name": "",
            "weight": "Normal",
            "base_group": "handwrite",
            "flag": "require",
        },
        {
            "map_name": "$MCMFont",
            "font_name": "",
            "weight": "Normal",
            "base_group": "mcm",
            "flag": "option",
        },
        {
            "map_name": "$MCMMediumFont",
            "font_name": "",
            "weight": "Normal",
            "base_group": "mcm",
            "flag": "option",
        },
        {
            "map_name": "$MCMBoldFont",
            "font_name": "",
            "weight": "Normal",
            "base_group": "mcm",
            "flag": "option",
        },
        {
            "map_name": "$DragonFont",
            "font_name": "Dragon_script",  # fonts_core.swf に格納されている。他のspecial系も同様
            "weight": "Normal",
            "base_group": "special",
            "flag": "require",
        },
        {
            "map_name": "$FalmerFont",
            "font_name": "Falmer",
            "weight": "Normal",
            "base_group": "special",
            "flag": "require",
        },
        {
            "map_name": "$DwemerFont",
            "font_name": "Dwemer",
            "weight": "Normal",
            "base_group": "special",
            "flag": "require",
        },
        {
            "map_name": "$DaedricFont",
            "font_name": "Daedric",
            "weight": "Normal",
            "base_group": "special",
            "flag": "require",
        },
        {
            "map_name": "$MageScriptFont",
            "font_name": "Mage Script",
            "weight": "Normal",
            "base_group": "special",
            "flag": "require",
        },
        {
            "map_name": "$SkyrimSymbolsFont",
            "font_name": "SkyrimSymbols",
            "weight": "Normal",
            "base_group": "special",
            "flag": "require",
        },
        {
            "map_name": "$SkyrimBooks_UnreadableFont",
            "font_name": "SkyrimBooks_Unreadable",
            "weight": "Normal",
            "base_group": "special",
            "flag": "require",
        },
        {
            "map_name": "ControllerButtons",
            "font_name": "Controller  Buttons",  # スペースが2つで正しいことに注意
            "weight": "Normal",
            "base_group": "special",
            "flag": "require",
        },
        {
            "map_name": "ControllerButtonsInverted",
            "font_name": "Controller  Buttons inverted",  # スペースが2つで正しいことに注意
            "weight": "Normal",
            "base_group": "special",
            "flag": "require",
        },
        # {
        #     "map_name": "$CustomMap1",
        #     "font_name": "custom_font_name1",
        #     "weight": "Normal",
        #     "base_group": "custom",
        #     "flag": "option",
        # },  # 独自マップの書き方メモ
    ],
    # 文字が多すぎるので、別ファイルで初期化時に埋める data\validNameChars.txt
    # "valid_name_chars": "",
    # "cache": [
    #     # {
    #     #     # 読み込みキャッシュ対象のパス（swf_dirからの相対）絶対パスだと、swf_dirを移動させたらキャッシュが無効になるため。
    #     #     "swf_path": "fonts_example_every.swf",
    #     #     # フォーマットを定数化して解釈すること。
    #     #     "modified_date": "2026/01/01 00:00:00",
    #     #     # やっぱりハッシュの方が良いとなった際の予約。
    #     #     "hash": "",
    #     #     "font_names": ["example_every"],
    #     # },  # サンプル
    # ],
}
# デフォルトのvalidNameCharsのパス
DEFAULT_VALIDNAMECHARS_PATH = DATA_DIR / "validNameChars.txt"

# キャッシュデータのパス
CACHE_PATH = DATA_DIR / "cache.yml"
# キャッシュの中身サンプル
CACHE_DATA = [
    # {
    #     # 読み込みキャッシュ対象のパス（swf_dirからの相対）絶対パスだと、swf_dirを移動させたらキャッシュが無効になるため。
    #     "swf_path": "example/fonts_example.swf",
    #     # 時刻フォーマットを定数化して比較に齟齬がでないようにすること。
    #     "modified_date": "2026/01/01 00:00:00",
    #     # やっぱりハッシュの方が良いとなった際の予約。
    #     "hash": "",
    #     # 1SWFにはゼロから複数のフォント名が入っている想定。
    #     "font_names": ["example_every","example_book","example_handwrite"],
    # },
]

# サンプル画像拡張子
SAMPLE_IMG_EXT = [".png", ".jpg", ".jpeg"]
# サンプル画像ファイル名
SAMPLE_IMG_NAME = ["sample", "preview", "image"]

# 日付フォーマット
TIME_FORMAT = "%Y/%m/%d %H:%M:%S"

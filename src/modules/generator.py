import shutil
from pathlib import Path

from const import SKYRIM_FONTCONFIG_ENCODE, SKYRIM_INTERFACE_DIR_NAME
from models.cache import Cache
from models.preset import Preset


def preset_generator(
    preset: Preset, cache_data: Cache, use_fallback: bool = False
) -> Path:
    """設定に基づいて fontconfig.txt を生成する

    Args:
        preset: プリセット設定
        cache_data: キャッシュデータ
        use_fallback: Trueの場合、フォント指定が空でも fonts_core.swf を代替として使用
    """
    # 出力ディレクトリの準備
    out_dir = preset.output_dir
    # Interfaceフォルダ構造を維持して出力
    interface_out = out_dir / Path(SKYRIM_INTERFACE_DIR_NAME)
    interface_out.mkdir(parents=True, exist_ok=True)

    # 必要なSWFをキャッシュから特定
    used_fonts = {m["font_name"] for m in preset.mappings if m["font_name"]}

    # フォント指定が空で、フォールバック有効な場合
    if not used_fonts and use_fallback:
        # fonts_core.swf を代替として使用
        fallback_path = Path(__file__).parent.parent.parent / "data" / "fonts_core.swf"
        if fallback_path.exists():
            fallback_cache_entry = None
            # キャッシュから fonts_core.swf のエントリを探す
            for entry in cache_data:
                swf_rel_path = entry.get("swf_path", "")
                if "fonts_core" in str(swf_rel_path):
                    fallback_cache_entry = entry
                    break

            # もしキャッシュにない場合、新規エントリを作成
            if not fallback_cache_entry:
                from modules.swf_parser import swf_parser

                font_names = swf_parser(
                    swf_path=fallback_path, cache=cache_data, debug=False
                )
                fallback_cache_entry = {
                    "swf_path": str(fallback_path),
                    "font_names": font_names if font_names else [],
                }

            # 最初のフォント名をマッピングに使用（存在する場合）
            if fallback_cache_entry.get("font_names"):
                first_font = fallback_cache_entry["font_names"][0]
                used_fonts.add(first_font)
                print(
                    f"✅ フォールバック: fonts_core.swf の '{first_font}' を使用します"
                )

    # fontconfig.txtに書き出すパスのセット (例: "Interface/fonts_font1.swf")
    fontlib_paths = set()

    # 物理コピー用の情報リスト (ソースパスとファイル名)
    copy_tasks = []

    for entry in cache_data:
        swf_rel_path = entry.get("swf_path", "")
        font_names = entry.get("font_names", [])
        if any(f in used_fonts for f in font_names):
            # fontconfig.txt に書くパス（Interface/ファイル名）を作成
            swf_name = Path(swf_rel_path).name
            fontlib_paths.add(f"{str(SKYRIM_INTERFACE_DIR_NAME)}/{swf_name}")
            src_file = preset.swf_dir / swf_rel_path
            copy_tasks.append((src_file, swf_name))

    # フォント設定ファイルの内容リスト（最後に書き出す）
    lines = []

    # fontlib セクション
    for swf_path in sorted(list(fontlib_paths)):
        lines.append(f"fontlib \"{swf_path}\"")

    # map セクション
    for m in preset.mappings:
        map_name = m["map_name"]
        font_name = m["font_name"]
        weight = m["weight"]

        # フォント名が空の場合は、そのマップは出力しない（バニラ挙動への影響を避ける）
        if not font_name:
            continue

        # 書式例: map "$ConsoleFont" = "Arial" Normal
        lines.append(f"map \"{map_name}\" = \"{font_name}\" {weight}")

    # validNameChars セクション
    lines.append(f"validNameChars \"{preset.validnamechars}\"")

    # --- 3. fontconfig.txt / fontconfig_ja.txt の保存 ---
    config_file = interface_out / "fontconfig.txt"
    with open(config_file, "w", encoding=SKYRIM_FONTCONFIG_ENCODE) as f:
        f.write("\n".join(lines))
    config_file_ja = interface_out / "fontconfig_ja.txt"
    with open(config_file_ja, "w", encoding=SKYRIM_FONTCONFIG_ENCODE) as f:
        f.write("\n".join(lines))

    # --- 4. SWFファイルの物理コピー実行 ---
    for src_file, swf_name in copy_tasks:
        if src_file.exists():
            dest_file = interface_out / swf_name
            shutil.copy2(src_file, dest_file)
            print(f"✅ SWFをコピーしました (再帰対応): {swf_name}")
        else:
            print(f"⚠️ 警告: ファイルが元の場所に見つかりません: {src_file}")

    return interface_out / "fontconfig.txt"

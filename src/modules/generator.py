import shutil
from pathlib import Path

from const import SKYRIM_FONTCONFIG_ENCODE, SKYRIM_INTERFACE_DIR_NAME
from models.preset import Preset


def preset_generator(
    preset: Preset, use_fallback: bool = False, debug: bool = False
) -> Path:
    """設定に基づいて fontconfig.txt を生成する

    Args:
        preset: プリセット設定
        use_fallback: Trueの場合、フォント指定が空でも fonts_core.swf を代替として使用
        debug: Trueの場合、デバッグ情報を表示
    """
    # 出力ディレクトリの準備
    out_dir = preset.output_dir
    # Interfaceフォルダ構造を維持して出力
    interface_out = out_dir / Path(SKYRIM_INTERFACE_DIR_NAME)
    interface_out.mkdir(parents=True, exist_ok=True)

    # fontconfig.txtに書き出すパスのセット (例: "Interface/fonts_font1.swf")
    fontlib_paths = set()

    # 物理コピー用の情報リスト (ソースパスとファイル名)
    copy_tasks = []

    fallback_path = Path(__file__).parent.parent.parent / "data" / "fonts_core.swf"
    swf_dir = Path(getattr(preset, "swf_dir", ""))

    for mapping in preset.mappings:
        font_name = mapping.get("font_name", "")
        if not font_name:
            continue

        swf_rel_path = mapping.get("swf_path", "")

        src_file = None
        swf_name = ""

        if swf_rel_path:
            src_file = swf_dir / swf_rel_path
            swf_name = Path(swf_rel_path).name
        elif use_fallback:
            src_file = fallback_path
            swf_name = fallback_path.name

        if not src_file or not swf_name:
            continue

        # fontlib パスは "Interface/" プレフィックスを付けて記録 区切り文字はスラッシュであること。
        fontlib_paths.add(f"{str(SKYRIM_INTERFACE_DIR_NAME)}/{swf_name}")
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

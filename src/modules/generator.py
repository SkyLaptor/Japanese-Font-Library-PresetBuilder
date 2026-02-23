import shutil
from pathlib import Path

from const import FONTCONFIG_ENCODE, INTERFACE_DIR
from models.user_config import UserConfig


def config_generator(user_config: UserConfig) -> Path:
    """設定に基づいて fontconfig.txt を生成する"""
    # --- 1. 出力ディレクトリの準備 ---
    out_dir = user_config.output_dir
    # Interfaceフォルダ構造を維持して出力
    interface_out = out_dir / Path(INTERFACE_DIR)
    interface_out.mkdir(parents=True, exist_ok=True)

    # fontconfig.txtの内容
    lines = []

    # 1. FontLib セクション
    # 動的に必要なSWFを追加
    required_swfs = user_config.get_required_swfs()
    for swf in required_swfs:
        lines.append(f"fontlib \"{swf}\"")

    # 2. Map セクション
    for m in user_config.mappings:
        map_name = m["map_name"]
        font_name = m["font_name"]
        weight = m["weight"]

        # フォント名が空の場合は、そのマップは出力しない（バニラ挙動への影響を避ける）
        if not font_name:
            continue

        # スカイリムの形式: map "$ConsoleFont" = "Arial" Normal
        lines.append(f"map \"{map_name}\" = \"{font_name}\" {weight}")

    # 3. ValidNameChars セクション
    lines.append(f"validNameChars \"{user_config.valid_name_chars}\"")

    # --- 3. fontconfig.txt / fontconfig_ja.txt の保存 ---
    config_file = interface_out / "fontconfig.txt"
    with open(config_file, "w", encoding=FONTCONFIG_ENCODE) as f:
        f.write("\n".join(lines))
    config_file_ja = interface_out / "fontconfig_ja.txt"
    with open(config_file_ja, "w", encoding=FONTCONFIG_ENCODE) as f:
        f.write("\n".join(lines))

    # --- 4. SWFファイルのコピー ---
    for swf_rel_path in required_swfs:
        # swf_rel_path は "Interface/example.swf" という形式
        swf_name = Path(swf_rel_path).name

        # ソース（元ファイル）の特定
        # ユーザーが選択したSWFディレクトリの中から、ファイル名が一致するものを探す
        src_file = user_config.swf_dir / swf_name

        if src_file.exists():
            dest_file = interface_out / swf_name
            shutil.copy2(src_file, dest_file)
            print(f"SWFをコピーしました。: {swf_name}")
        else:
            # fonts_core.swfなどは元フォルダにない可能性があるので、
            # あればコピー、なければスキップ（警告）
            print(f"警告: コピー対象のSWFが見つかりません: {src_file}")

    return config_file

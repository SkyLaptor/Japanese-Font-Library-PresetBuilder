import shutil
from pathlib import Path

from const import FONTCONFIG_ENCODE, INTERFACE_DIR
from models.cache import Cache
from models.preset import Preset


def preset_generator(preset: Preset, cache_data: Cache) -> Path:
    """設定に基づいて fontconfig.txt を生成する"""
    # --- 1. 出力ディレクトリの準備 ---
    out_dir = preset.output_dir
    # Interfaceフォルダ構造を維持して出力
    interface_out = out_dir / Path(INTERFACE_DIR)
    interface_out.mkdir(parents=True, exist_ok=True)

    # --- 2. 必要なSWFをキャッシュから特定 (ここを先にやる) ---
    used_fonts = {m["font_name"] for m in preset.mappings if m["font_name"]}
    needed_swfs = set()

    for entry in cache_data:
        swf_rel_path = entry.get("swf_path", "")
        font_names = entry.get("font_names", [])
        if any(f in used_fonts for f in font_names):
            # fontconfig.txt に書くパス（Interface/ファイル名）を作成
            needed_swfs.add(f"{str(INTERFACE_DIR)}/{Path(swf_rel_path).name}")

    # fontconfig.txtの内容
    lines = []

    # 1. FontLib セクション (特定した needed_swfs を使う)
    for swf_path in sorted(list(needed_swfs)):
        lines.append(f"fontlib \"{swf_path}\"")

    # 2. Map セクション
    for m in preset.mappings:
        map_name = m["map_name"]
        font_name = m["font_name"]
        weight = m["weight"]

        # フォント名が空の場合は、そのマップは出力しない（バニラ挙動への影響を避ける）
        if not font_name:
            continue

        # スカイリムの形式: map "$ConsoleFont" = "Arial" Normal
        lines.append(f"map \"{map_name}\" = \"{font_name}\" {weight}")

    # 3. ValidNameChars セクション
    lines.append(f"validNameChars \"{preset.valid_name_chars}\"")

    # --- 3. fontconfig.txt / fontconfig_ja.txt の保存 ---
    config_file = interface_out / "fontconfig.txt"
    with open(config_file, "w", encoding=FONTCONFIG_ENCODE) as f:
        f.write("\n".join(lines))
    config_file_ja = interface_out / "fontconfig_ja.txt"
    with open(config_file_ja, "w", encoding=FONTCONFIG_ENCODE) as f:
        f.write("\n".join(lines))

    # --- 4. SWFファイルのコピー ---
    # 実際に使っているフォント名のセット
    used_fonts = {m["font_name"] for m in preset.mappings if m["font_name"]}

    needed_swfs = set()

    # キャッシュデータ(リスト)をループで回す
    for entry in cache_data:
        swf_rel_path = entry.get("swf_path", "")
        font_names = entry.get("font_names", [])

        # このSWFの中に、今回使っているフォントが一つでも含まれているか？
        if any(f in used_fonts for f in font_names):
            # ファイル名だけ抽出してセットに追加
            needed_swfs.add(Path(swf_rel_path).name)

    # 特定したSWFをコピー
    for swf_name in needed_swfs:
        src_file = preset.swf_dir / swf_name
        if src_file.exists():
            dest_file = interface_out / swf_name
            shutil.copy2(src_file, dest_file)
            print(f"✅ SWFをコピーしました: {swf_name}")
        else:
            print(f"⚠️ 警告: コピー元のファイルが見つかりません: {src_file}")

    return config_file

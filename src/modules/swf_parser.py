import argparse
import re
import struct
import sys
import zlib
from datetime import datetime
from pathlib import Path

from const import ENCODE, SETTINGS_FILE, TIME_FORMAT
from utils.dprint import dprint


def main():
    parser = argparse.ArgumentParser(description="フォントSWFをパースする")

    parser.add_argument(
        "swf_path",
        type=str,
        help="フォントSWFファイルのパス",
    )
    parser.add_argument(
        "--cache",
        type=list,
        default=[],
        help="フォントSWFの読込キャッシュ",
    )
    parser.add_argument(
        "--settings_path",
        type=str,
        default=SETTINGS_FILE,
        help="システム設定ファイルのパス",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="デバッグ表示の有効化",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    action_swf_parser(**vars(args))


def action_swf_parser(swf_path: str, cache: list, debug: bool, **_):
    swf_path = Path(swf_path)

    print(f"swf_path: {swf_path.resolve()}")
    if not swf_path.exists():
        raise FileExistsError(f"ファイルが存在しません。: {swf_path}")

    print("指定したフォントSWF内のフォント名一覧")
    font_names = swf_parser(swf_path=swf_path, cache=cache, debug=debug)

    for font_name in font_names:
        print(font_name)


def swf_parser(swf_path: Path, cache: list, debug: bool = False) -> list[str]:
    """
    SWFバイナリを高速スキャンし、DefineFontタグから本物のフォント名だけを抽出します。
    """
    # 比較用に更新日時を文字列化（保存形式に合わせて相対パスで）
    current_mtime = datetime.fromtimestamp(swf_path.stat().st_mtime).strftime(
        TIME_FORMAT
    )

    for entry in cache:
        # 1. パスが一致するか (entry["swf_path"] 自体がパス文字列)
        # ※ 相対パスか絶対パスか、プロジェクトのルールに合わせます
        if entry.get("swf_path") == str(swf_path) or str(swf_path).endswith(
            entry.get("swf_path", "")
        ):

            # 2. 更新日時が一致するか
            if entry.get("modified_date") == current_mtime:
                dprint(f"キャッシュを使用: {swf_path.name}", debug)
                return entry["font_names"]

            # パスは合ってるけど日時が違う場合は、このentryは古いので無視して解析へ
            break

    try:
        with open(swf_path, 'rb') as f:
            raw_data = f.read()
    except Exception as e:
        print(f"ファイルの読み込みに失敗しました: {e}")
        return []

    # 1. 圧縮の解除
    if raw_data[:3] == b'CWS':
        # Header (8byte) はそのまま、それ以降を解凍
        try:
            data = raw_data[:8] + zlib.decompress(raw_data[8:])
        except Exception:
            data = raw_data
    else:
        data = raw_data

    font_names = set()
    data_size = len(data)

    # 2. 高速スキャン (whileループでジャンプを制御)
    i = 0
    while i < data_size - 10:
        # 2バイト読んでタグヘッダーとして解釈
        tag_header = struct.unpack('<H', data[i : i + 2])[0]
        tag_type = tag_header >> 6
        tag_len = tag_header & 0x3F

        # DefineFont2 (48) or DefineFont3 (75) をターゲットにする
        if tag_type in (48, 75):
            read_pos = i + 2
            actual_len = tag_len
            if tag_len == 0x3F:  # 長いタグ
                if read_pos + 4 > data_size:
                    break
                actual_len = struct.unpack('<I', data[read_pos : read_pos + 4])[0]
                read_pos += 4

            # --- フィルタリング条件 ---
            # 条件1: 11MBのフォントSWFなら、本物は最低でも数百バイト〜数MBある
            # 偶然ヒットしたゴミ（数バイト〜数十バイト）をここで一気に弾く
            if actual_len < 500:
                i += 1
                continue

            # タグの末尾がデータ範囲内かチェック
            if read_pos + actual_len > data_size:
                i += 1
                continue

            # タグの中身を確認
            # [FontID:2][Flags:1][Language:1][NameLen:1][Name:NameLen]
            # なので NameLen は content の 4 バイト目にある
            try:
                name_len = data[read_pos + 4]
                if 4 <= name_len < 64:  # 名前が短すぎず、現実的な長さか
                    name_start = read_pos + 5
                    name_end = name_start + name_len
                    name_bytes = data[name_start:name_end]
                    font_name = name_bytes.decode(ENCODE, errors='ignore').rstrip('\0')

                    # 条件2: 英数字、スペース、ハイフン、アンダースコアのみ許可
                    if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\s_\-]+$', font_name):
                        font_names.add(font_name)

                        # 【重要】本物を見つけたら、そのタグの終わりまで一気にジャンプ！
                        # これでタグ内部のバイナリを誤検知するのを防ぎます
                        i = read_pos + actual_len
                        continue
            except Exception:
                pass

        # 本物が見つからない場合は1バイトずつ進む
        i += 1

    return sorted(list(font_names))


# テスト用
if __name__ == "__main__":
    main()

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from const import SETTINGS_FILE, TIME_FORMAT
from models.settings import Settings
from src.const import ENCODE
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


def action_swf_parser(swf_path: str, cache: list, settings_path: str, debug: bool, **_):
    # システム設定ファイルの読み込み
    settings_path = Path(settings_path)
    settings = Settings(settings_path)
    settings.load()
    dprint(str(settings.ffdec_cli), debug)

    swf_path = Path(swf_path)

    print(f"swf_path: {swf_path.resolve()}")
    if not swf_path.exists():
        raise FileExistsError(f"ファイルが存在しません。: {swf_path}")

    print("指定したフォントSWF内のフォント名一覧")
    for font_name in swf_parser(
        swf_path=swf_path, cache=cache, settings=settings, debug=debug
    ):
        print(font_name)


def swf_parser(
    swf_path: Path, cache: list, settings: set, debug: bool = False
) -> list[str]:
    """FFDecのdumpSWFからフォント名を抽出する"""
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
                dprint(f"キャッシュヒット!: {swf_path.name}", debug)
                return entry["font_names"]

            # パスは合ってるけど日時が違う場合は、このentryは古いので無視して解析へ
            break

    try:
        # コマンド実行
        cmd = [str(settings.ffdec_cli), "-dumpSWF", str(swf_path.resolve())]
        dprint(f"CMD: {cmd}", debug)
        print(f"内部フォント名を確認中...: {str(swf_path.resolve())}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding=ENCODE,
            errors="ignore",
        )

        # "fn: \"フォント名\"" を探す正規表現
        pattern = re.compile(r'fn: "([^"]+)"')

        matches = pattern.findall(result.stdout)

        if debug:
            print(f"FFDec dump for {swf_path.name} finished.")

        return sorted(list(set(matches)))

    except Exception as e:
        print(f"Error: {e}")
        return []


# テスト用
if __name__ == "__main__":
    main()

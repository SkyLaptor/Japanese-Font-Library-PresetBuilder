from datetime import datetime
from pathlib import Path

import yaml

from src.const import (
    ENCODE,
    TIME_FORMAT,
)


class Cache:
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path  # パスを保持する変数を分ける
        self.data = []  # 中身を data にする

        if not self.cache_path.exists():
            print("キャッシュファイルが存在しないため、空ファイルを生成します。")
            self.save()
        else:
            self.load()

    def load(self):
        """YAMLファイルからキャッシュを読み込む"""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding=ENCODE) as f:
                    loaded_data = yaml.safe_load(f)
                    if isinstance(loaded_data, list):
                        self.data = loaded_data
            except Exception as e:
                print(f"キャッシュの読み込みに失敗しました: {e}")

    def save(self):
        """現在のキャッシュをYAMLファイルに保存する"""
        try:
            # 親ディレクトリがなければ作成
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding=ENCODE) as f:
                # Dumper を指定して、アンカー/エイリアスを無効化する
                class NoAliasDumper(yaml.SafeDumper):
                    def ignore_aliases(self, data):
                        return True

                yaml.dump(self.data, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            print(f"キャッシュの保存に失敗しました: {e}")

    def update_swf_cache(self, swf_path: Path, font_names: list, swf_dir: Path):
        """解析したフォント名をキャッシュに保存/更新する"""
        try:
            rel_path = str(swf_path.relative_to(swf_dir))
        except ValueError:
            rel_path = str(swf_path)

        mtime = datetime.fromtimestamp(swf_path.stat().st_mtime).strftime(TIME_FORMAT)

        found = False
        for entry in self.data:
            if entry["swf_path"] == rel_path:
                entry["modified_date"] = mtime
                entry["font_names"] = font_names
                found = True
                break

        if not found:
            self.data.append(
                {
                    "swf_path": rel_path,
                    "modified_date": mtime,
                    "font_names": font_names,
                    "hash": "",
                }
            )

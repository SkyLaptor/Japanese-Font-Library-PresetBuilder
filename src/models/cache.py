from datetime import datetime
from pathlib import Path

import yaml

from src.const import (
    ENCODE,
    TIME_FORMAT,
)


class Cache:
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.load()

    def load(self):
        """YAMLファイルからキャッシュを読み込む"""
        self.data = []
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding=ENCODE) as f:
                    loaded_data = yaml.safe_load(f) or []
                    if isinstance(loaded_data, list):
                        self.data = loaded_data
            except Exception as e:
                print(f"キャッシュの読み込みに失敗しました: {e}")

    def save(self):
        """YAMLファイルにキャッシュを保存する"""
        try:
            # 親ディレクトリがなければ作成
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding=ENCODE) as f:
                # Dumper を指定して、アンカー/エイリアスを無効化する
                class NoAliasDumper(yaml.SafeDumper):
                    def ignore_aliases(self, data):
                        return True

                yaml.dump(
                    self.data,
                    f,
                    Dumper=NoAliasDumper,
                    allow_unicode=True,
                    sort_keys=False,
                )
        except Exception as e:
            print(f"キャッシュの保存に失敗しました: {e}")

    def update(self, swf_path: Path, font_names: list, swf_dir: Path):
        """解析したフォント名とそのフォントSWFパスをキャッシュに保存/更新する"""
        # 絶対パスをswf_dirからの相対パスに変換して保存することで、環境が変わってもキャッシュが有効になるようにする
        try:
            rel_path = str(swf_path.relative_to(swf_dir))
        except ValueError:
            rel_path = str(swf_path)

        modified_date = datetime.fromtimestamp(swf_path.stat().st_mtime).strftime(
            TIME_FORMAT
        )

        # キャッシュ内に同じswf_pathがあれば更新、なければ追加
        found = False
        for entry in self.data:
            if entry["swf_path"] == rel_path:
                entry["modified_date"] = modified_date
                entry["font_names"] = font_names
                found = True
                break

        if not found:
            self.data.append(
                {
                    "swf_path": rel_path,
                    "modified_date": modified_date,
                    "font_names": font_names,
                    "hash": "",
                }
            )

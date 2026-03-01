from pathlib import Path
from typing import Dict, List

from modules.generator import preset_generator
from modules.swf_parser import swf_parser
from utils.dprint import dprint


class MainController:
    def __init__(self, settings, preset, cache, debug: bool = False):
        self.settings = settings
        self.preset = preset
        self.cache = cache
        self.debug = debug

    def _get_swf_base_dir(self) -> Path:
        """settings.swf_dir を基準ディレクトリとして返す。"""
        if not self.settings.swf_dir:
            raise ValueError("settings.swf_dir が未設定です。")

        base_dir = Path(self.settings.swf_dir).resolve()
        if not base_dir.exists() or not base_dir.is_dir():
            raise ValueError(f"settings.swf_dir が不正です: {base_dir}")
        return base_dir

    def to_relative_swf_path(self, swf_path: str | Path) -> str:
        """絶対SWFパスを settings.swf_dir 基準の相対パスへ変換する。"""
        base_dir = self._get_swf_base_dir()
        source_path = Path(swf_path).resolve()
        return source_path.relative_to(base_dir).as_posix()

    def resolve_absolute_swf_path(self, swf_path: str | Path) -> Path:
        """相対/絶対SWFパスを絶対パスへ解決する。"""
        target_path = Path(swf_path)
        if target_path.is_absolute():
            return target_path.resolve()

        base_dir = self._get_swf_base_dir()
        return (base_dir / target_path).resolve()

    def scan_swf_directory(self, swf_dir_path: Path) -> List[Dict]:
        """SWFディレクトリをスキャンし、UI表示用の結果を返す。

        Returns list of dicts: {"swf_path": Path, "font_names": List[str]}
        """
        scan_results = []

        for swf_path in swf_dir_path.rglob("*.swf"):
            font_names = swf_parser(
                swf_path=swf_path, cache=self.cache.data, debug=self.debug
            )
            if font_names:
                try:
                    # cache has `update` method that records relative path and font names
                    self.cache.update(
                        swf_path=swf_path, font_names=font_names, swf_dir=swf_dir_path
                    )
                except Exception:
                    # if cache API differs, ignore to avoid crashing UI
                    pass
                scan_results.append({"swf_path": swf_path, "font_names": font_names})

        # SWFファイル名でソート
        return sorted(
            scan_results,
            key=lambda x: str(Path(x.get("swf_path", "")).name),
        )

    def normalize_scan_results_for_ui(
        self, scan_results: List[Dict], swf_dir_path: Path
    ) -> List[Dict]:
        """スキャン結果をUI表示向けに正規化し、絶対パスで返す。"""
        normalized = []
        base_dir = Path(swf_dir_path).resolve()

        for item in scan_results:
            swf_path = item.get("swf_path")
            if not swf_path:
                continue

            abs_path = Path(swf_path).resolve()
            try:
                rel_path = self.to_relative_swf_path(abs_path)
            except Exception:
                try:
                    rel_path = str(abs_path.relative_to(base_dir))
                except Exception:
                    continue

            try:
                ui_abs_path = self.resolve_absolute_swf_path(rel_path)
            except Exception:
                ui_abs_path = abs_path

            normalized.append(
                {
                    "swf_path": str(ui_abs_path),
                    "font_names": item.get("font_names", []) or [],
                }
            )

        return normalized

    def process_single_swf(self, swf_path: Path) -> Dict:
        """単一のSWFファイルをスキャンし、フォント情報を返す。

        Returns: {"swf_path": Path, "font_names": List[str]}
        ファイルが存在しないか解析に失敗した場合も、空のfont_namesで返す.
        """
        if not swf_path.exists():
            dprint(f"ファイルが見つかりません: {swf_path}", self.debug)
            return {"swf_path": swf_path, "font_names": []}

        try:
            font_names = swf_parser(
                swf_path=swf_path, cache=self.cache.data, debug=self.debug
            )
            # font_namesがNoneまたは空の場合も、辞書形式で返す（常にデータ構造を統一）
            return {
                "swf_path": swf_path,
                "font_names": font_names if font_names else [],
            }
        except Exception as e:
            print(f"単一ファイルのスキャンに失敗: {swf_path} - {e}")
            return {"swf_path": swf_path, "font_names": []}

    def validate_required_mappings(self) -> list:
        """必須マッピング(require)でフォント未指定の map_name を返す"""
        missing = []
        for m in self.preset.mappings:
            if m.get("flag") == "require" and (
                not m.get("font_name") or m.get("font_name") == ""
            ):
                missing.append(m.get("map_name"))
        return missing

    def _update_preset_mapping(
        self,
        map_name: str,
        font_name: str,
        swf_path: str = "",
        *,
        save: bool = False,
    ) -> bool:
        """map_name に対応する preset mapping を更新する内部処理。"""
        current_font = self.preset.get_mapping_font_name(map_name)
        current_swf = self.preset.get_mapping_swf_path(map_name)

        next_font = font_name or ""
        next_swf = swf_path or ""

        if current_font == next_font and current_swf == next_swf:
            return False

        self.preset.update_mapping(map_name, next_font, next_swf)
        if save:
            self.preset.save()
        return True

    def update_mapping_from_ui(
        self,
        map_name: str,
        font_name: str,
        selected_swf_path: str | Path | None = None,
        *,
        save: bool = False,
    ) -> bool:
        """UI入力を受け取り、必要なパス変換を行った上で mapping を更新する。"""
        normalized_font = font_name or ""

        if not normalized_font:
            return self._update_preset_mapping(map_name, "", "", save=save)

        if not selected_swf_path:
            raise ValueError("フォントが指定されていますが SWF パスがありません。")

        try:
            rel_swf_path = self.to_relative_swf_path(selected_swf_path)
        except ValueError as e:
            raise ValueError(
                "選択されたSWFが settings.swf_dir の外側、または swf_dir 未設定です。"
            ) from e

        return self._update_preset_mapping(
            map_name,
            normalized_font,
            rel_swf_path,
            save=save,
        )

    def find_missing_fonts(self, available_font_names: set) -> list:
        """現在のスキャン結果に存在しない設定済みフォントを返す"""
        not_found = []
        for m in self.preset.mappings:
            f_name = m.get("font_name")
            if f_name and f_name not in available_font_names:
                not_found.append((m.get("map_name"), f_name))
        return not_found

    def generate_preset(self, output_dir: Path, use_fallback: bool = False):
        """プリセットを指定フォルダに出力するコア処理。

        Args:
            output_dir: 出力先ディレクトリ
            use_fallback: Trueの場合、フォント指定が空でも fonts_core.swf を使用して出力

        Returns:
            Path: 生成されたfontconfig.txtのパス
        """
        # 更新
        self.preset.output_dir = Path(output_dir)

        swf_dir = self._get_swf_base_dir() if self.settings.swf_dir else Path()
        self.preset.swf_dir = swf_dir

        # 生成前に、Preset 内の相対パスを settings ルールで絶対パスへ解決可能か確認
        for rel_swf_path in self.preset.get_mapping_swf_paths():
            try:
                self.resolve_absolute_swf_path(rel_swf_path)
            except Exception as e:
                print(f"SWFパス解決に失敗しました: {rel_swf_path} ({e})")

        self.preset.save()

        # 生成処理（IOや重い処理を含む）
        out_file = preset_generator(self.preset, use_fallback, self.debug)
        return out_file

    def save_preset(self):
        """プリセット保存のコア処理（例外が起きたら呼び出し側でハンドル）"""
        self.preset.save()

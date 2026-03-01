import os
import shutil
import time
from pathlib import Path

import yaml
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from const import (
    ALLOW_MAPPING_CATEGORY,
    CACHE_FILE,
    DEFAULT_PRESET_FILE,
    ENCODE,
    MAIN_WINDOW_TITLE,
    PRESETS_DIR,
    SETTINGS_FILE,
    SKYRIM_CORE_FONT_SWF,
    SKYRIM_CORE_FONT_SWF_IMAGE_DIR,
)
from models.cache import Cache
from models.preset import Preset
from models.settings import Settings
from src.gui.main_controller import MainController
from src.modules.find_preview_image import find_preview_image
from utils.dprint import dprint

SWF_FILE_LINE_PREFIX = "SWF: "
FONT_NAME_LINE_PREFIX = "  - "
UNDEFINE_FONT_NAME = "未設定"


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class PreviewImageDialog(QDialog):
    def __init__(self, image_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("プレビュー画像")
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        self.image_label = ClickableLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setMinimumSize(1, 1)
        self.image_label.clicked.connect(self.accept)

        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.image_label.setText("画像を読み込めませんでした")
            self._original_pixmap = None
            return

        self._original_pixmap = pixmap
        self.resize(pixmap.size())
        self._update_scaled_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self):
        if not self._original_pixmap:
            return

        viewport_size = self.scroll_area.viewport().size()
        if viewport_size.width() <= 0 or viewport_size.height() <= 0:
            return

        scaled = self._original_pixmap.scaled(
            viewport_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)


class MainWindow(QMainWindow):
    def __init__(
        self, settings: Settings, preset: Preset, cache: Cache, debug: bool = False
    ):
        super().__init__()
        self.settings = settings
        self.preset = preset
        self.cache = cache
        self.debug = debug
        self.controller = MainController(
            settings=settings,
            preset=preset,
            cache=cache,
            debug=self.debug,
        )
        self.scanned_swf_entries = []
        self._pending_mapping_swf_paths = {}
        self.current_preview_image_path: Path | None = None
        self.startup_aborted = False
        # プリセット変更フラグ
        # 何か設定を操作するようなアクションを起こしたらTrueに、プリセットを保存するアクションでFalseにすること！
        self.preset_is_dirty = False

        # ウィンドウ
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.resize(1100, 700)
        widget_main = QWidget()
        self.setCentralWidget(widget_main)
        # 全ての画面コンポーネントの基底となる「垂直」レイアウト
        vboxlayout_main = QVBoxLayout(widget_main)

        # --- 上部 ---
        # 分割の必要がないので、そのままメインレイアウトに挿入。
        # メインレイアウトは垂直レイアウトなので上から順に入る。
        # フォントSWF読み込みフォルダ選択エリア
        self.setup_swf_dir_selection(vboxlayout_main)
        # プリセット選択エリア
        self.setup_preset_selection(vboxlayout_main)

        # --- 中央 ---
        # 左右に分割したいので一旦「水平」レイアウトを用意して部品を挿入し、
        # それをメインの垂直レイアウトに挿入する。
        # 左から順に入る。
        # 中央分割用水平レイアウト
        hboxlayout_center = QHBoxLayout()
        # フォント名一覧
        self.setup_font_names(hboxlayout_center)
        # カテゴリ別マッピング
        self.setup_mappings(hboxlayout_center)
        # 中央分割用水平レイアウトをメインレイアウトに挿入
        vboxlayout_main.addLayout(hboxlayout_center)

        # --- 下部：実行エリア ---
        # validNameCharsエリア
        self.setup_validnamechars_input(vboxlayout_main)

        bottom_area = QVBoxLayout()  # 垂直レイアウトで入力欄とボタンを分ける

        # --- ボタンエリア ---
        save_layout = QHBoxLayout()

        btn_save_config = QPushButton("現在のユーザープリセット設定を保存")
        btn_save_config.setFixedHeight(45)
        btn_save_config.clicked.connect(self.on_save_current_preset_clicked)

        btn_generate = QPushButton("ユーザープリセットを出力")
        btn_generate.setFixedHeight(45)
        btn_generate.setStyleSheet(
            "background-color: #2c3e50; color: white; font-weight: bold; font-size: 14px;"
        )
        btn_generate.clicked.connect(self.on_generate_clicked)

        save_layout.addWidget(btn_save_config)
        save_layout.addWidget(btn_generate)
        # ボタンのレイアウトを bottom_area に入れる
        bottom_area.addLayout(save_layout)

        # レイアウトを正しく組み立て
        # validNameCharsと保存などのボタンが入ったレイアウトを設定
        vboxlayout_main.addLayout(bottom_area)

        # 画面起動時の初期動作
        # 初期値を読み込んだり起動環境を確認したり
        self.window_init()

    def window_init(self):
        # settings.yml に swf_dir が設定されていれば起動時に読み込む
        if not self.settings.swf_dir:
            return

        swf_dir = Path(self.settings.swf_dir)
        if not swf_dir.exists() or not swf_dir.is_dir():
            dprint(
                f"settings.yml の swf_dir が無効なため未設定に戻します: {swf_dir}",
                self.debug,
            )
            self.settings.swf_dir = ""
            self.settings.save()
            self.label_swf_dir_path.setText("参照中のSWFフォルダ: (未設定)")
            self.button_load_swf_dir.setEnabled(False)
            return

        self.label_swf_dir_path.setText(f"参照中のSWFフォルダ: {str(swf_dir)}")
        self.button_load_swf_dir.setEnabled(True)
        if not self.ensure_system_fonts_core(swf_dir):
            self.startup_aborted = True
            return
        self.refresh_font_names_list(swf_dir)

    def ensure_system_fonts_core(self, swf_dir: Path) -> bool:
        """SWFフォルダ内の system に必須アセットを配置する。"""
        target_core = swf_dir / "system" / "fonts_core.swf"
        target_system_dir = target_core.parent

        if not SKYRIM_CORE_FONT_SWF.exists():
            QMessageBox.critical(
                self,
                "エラー",
                f"コピー元が見つかりません:\n{SKYRIM_CORE_FONT_SWF}",
            )
            return False

        if (
            not SKYRIM_CORE_FONT_SWF_IMAGE_DIR.exists()
            or not SKYRIM_CORE_FONT_SWF_IMAGE_DIR.is_dir()
        ):
            QMessageBox.critical(
                self,
                "エラー",
                f"コピー元フォルダが見つかりません:\n{SKYRIM_CORE_FONT_SWF_IMAGE_DIR}",
            )
            return False

        try:
            target_system_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SKYRIM_CORE_FONT_SWF, target_core)

            for sample_file in SKYRIM_CORE_FONT_SWF_IMAGE_DIR.iterdir():
                if sample_file.is_file():
                    shutil.copy2(sample_file, target_system_dir / sample_file.name)

            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                "system配下アセットの配置に失敗しました。\n"
                f"コピー元: {SKYRIM_CORE_FONT_SWF}\n"
                f"コピー元フォルダ: {SKYRIM_CORE_FONT_SWF_IMAGE_DIR}\n"
                f"コピー先: {target_system_dir}\n"
                f"詳細: {e}",
            )
            return False

    def setup_swf_dir_selection(self, layout):
        """SWFフォルダ選択レイアウトのセットアップ"""
        hboxlayout_swf_dir = QHBoxLayout()

        # SWFフォルダのパス表示ラベル
        self.label_swf_dir_path = QLabel()
        label_swf_dir_path_prefix = "参照中のSWFフォルダ: "
        swf_dir = Path(self.settings.swf_dir) if self.settings.swf_dir else None
        # SWFフォルダが設定されていて、かつ存在しているか。
        if swf_dir and swf_dir.exists():
            # resolveしなくても、もともと絶対パスで入ってる。
            self.label_swf_dir_path.setText(f"{label_swf_dir_path_prefix}{swf_dir}")
        else:
            self.label_swf_dir_path.setText(f"{label_swf_dir_path_prefix}(未設定)")

        # SWFフォルダ閲覧ボタン
        button_browse_swf_dir = QPushButton("フォルダを開く")
        button_browse_swf_dir.clicked.connect(self.on_browse_swf_dir_clicked)

        # SWFフォルダ読み込みボタン
        self.button_load_swf_dir = QPushButton("読み込む")
        self.button_load_swf_dir.clicked.connect(self.on_load_swf_dir_clicked)
        self.button_load_swf_dir.setEnabled(bool(self.settings.swf_dir))

        # レイアウトへ各種部品の挿入
        hboxlayout_swf_dir.addWidget(self.label_swf_dir_path, stretch=1)
        hboxlayout_swf_dir.addWidget(button_browse_swf_dir)
        hboxlayout_swf_dir.addWidget(self.button_load_swf_dir)

        layout.addLayout(hboxlayout_swf_dir)

    def on_browse_swf_dir_clicked(self):
        """SWFフォルダ閲覧ボタン押下時のアクション"""
        if self.settings.swf_dir:
            reply = QMessageBox.warning(
                self,
                "SWFフォルダ変更の確認",
                "すでにSWFフォルダが設定されています。\n"
                "フォルダを変更すると、現在のプリセット設定と不整合が起きる可能性があります。\n\n"
                "このまま変更しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        dir_path = QFileDialog.getExistingDirectory(
            self, "フォントSWFが含まれるフォルダを選択"
        )
        if dir_path:
            p = Path(dir_path)
            if not self.ensure_system_fonts_core(p):
                return
            self.settings.swf_dir = str(p)
            self.settings.save()
            self.label_swf_dir_path.setText(f"参照中のSWFフォルダ: {str(p)}")
            self.button_load_swf_dir.setEnabled(True)  # ボタンを有効化
            self.refresh_font_names_list(p)

    def on_load_swf_dir_clicked(self):
        """SWFフォルダ読み込みボタン押下時のアクション"""
        # SWFフォルダが設定されていて、かつ存在しているか。
        swf_dir = Path(self.settings.swf_dir) if self.settings.swf_dir else None
        if swf_dir and swf_dir.exists():
            if not self.ensure_system_fonts_core(swf_dir):
                return
            self.refresh_font_names_list(swf_dir)
            # QMessageBox.information(self, "完了", "フォルダの内容を読み込みました。")
        else:
            QMessageBox.warning(self, "エラー", "フォルダが見つかりません。")

    def refresh_font_names_list(self, swf_dir_path: Path):
        """フォント名一覧を更新する（シンプル実装版）"""
        # フォント名一覧更新処理中ダイアログを表示
        message = (
            "フォントの一覧を更新しています...\n"
            "※フォントファイル数が多い場合、解析に時間がかかることがあります。"
        )
        progress = QProgressDialog(message, None, 0, 0, self)
        progress.setWindowTitle("処理中")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QGuiApplication.processEvents()

        try:
            # 1. フォルダスキャン実行
            scan_start = time.perf_counter()
            raw_list = self.controller.scan_swf_directory(swf_dir_path)
            scan_elapsed_ms = (time.perf_counter() - scan_start) * 1000

            # 2. UI表示向けにパスを正規化（Controllerに委譲）
            new_list = self.controller.normalize_scan_results_for_ui(
                raw_list, swf_dir_path
            )

            # 3. 保存と反映
            self.scanned_swf_entries = new_list
            self.cache.save()
            dprint(
                f"スキャンが完了しました: {len(self.scanned_swf_entries)} ファイル / {scan_elapsed_ms:.1f} ms",
                self.debug,
            )

            # UI反映
            self.refresh_ui_from_scan_results()

        except Exception as e:
            msg = "フォント名一覧の更新中にエラーが発生しました:"
            print(f"{msg} {e}")
            import traceback

            traceback.print_exc()
            QMessageBox.critical(self, "エラー", f"{msg}\n{e}")
        finally:
            progress.close()

    def setup_preset_selection(self, layout):
        """プリセット選択レイアウトのセットアップ"""
        groupbox_preset = QGroupBox("プリセット管理")
        boxlayout_preset = QHBoxLayout(groupbox_preset)

        # 1. プリセット選択
        boxlayout_preset.addWidget(QLabel("プリセット:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        self.refresh_preset_list()  # ファイル一覧を取得
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        boxlayout_preset.addWidget(self.preset_combo, stretch=1)

        # 2. 再読み込みボタン
        btn_reload = QPushButton("再読み込み")
        btn_reload.clicked.connect(self.on_reload_preset_clicked)
        boxlayout_preset.addWidget(btn_reload)

        # 3. 別名保存ボタン
        btn_save_as = QPushButton("別名で保存...")
        btn_save_as.clicked.connect(self.on_preset_save_as_clicked)
        boxlayout_preset.addWidget(btn_save_as)

        # レイアウトに組み立てた部品を挿入
        layout.addWidget(groupbox_preset)

    def refresh_preset_list(self):
        """PRESETS_DIR 内のYAMLをリストアップしてコンボボックスにセット"""

        if not PRESETS_DIR.exists():
            PRESETS_DIR.mkdir(parents=True, exist_ok=True)

        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()

        current_name = self.preset.preset_path.stem

        presets = sorted(list(PRESETS_DIR.glob("*.yml")))
        for p in presets:
            self.preset_combo.addItem(p.stem)

        self.preset_combo.setCurrentText(current_name)
        self.preset_combo.blockSignals(False)

    def refresh_ui_from_config(self):
        """現在の self.preset の内容を UI（各コンボボックス等）に再反映させる"""
        # ValidNameCharsを更新
        self.lineedit_validnamechars.setText(self.preset.validnamechars)

        # 各フォントマッピングのコンボボックスを更新
        for map_name, combo in self.combos.items():
            font_name = self.preset.get_mapping_font_name(map_name)
            combo.blockSignals(True)
            # もし現在のリストにないフォント名なら追加して選択
            if font_name and combo.findData(font_name) == -1:
                combo.addItem(self.format_mapping_font_label(font_name), font_name)

            idx = combo.findData(font_name if font_name else "")
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)

        # 未保存フラグをリセット
        self.preset_is_dirty = False
        self.setWindowTitle(MAIN_WINDOW_TITLE)

    def setup_font_names(self, layout):
        left_group = QGroupBox("フォルダ内に存在するフォント名")
        left_layout = QVBoxLayout(left_group)

        # フォント名検索
        self.lineedit_font_search = QLineEdit()
        self.lineedit_font_search.setPlaceholderText("フォント名を検索...")
        self.lineedit_font_search.textChanged.connect(self.on_font_search_text_changed)
        left_layout.addWidget(self.lineedit_font_search)

        # フォントリスト
        self.list_widget_font_names = QListWidget()
        # 項目が選択されたらプレビューを更新するシグナルを接続
        self.list_widget_font_names.itemSelectionChanged.connect(
            self.on_font_selection_changed
        )
        left_layout.addWidget(self.list_widget_font_names, stretch=2)

        # ★プレビュー画像表示エリア
        self.preview_label = ClickableLabel("プレビュー")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.clicked.connect(self.on_preview_label_clicked)
        self.preview_label.setCursor(Qt.ArrowCursor)

        # 「自分からはサイズを主張しない（親のレイアウトに従う）」という設定
        self.preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.preview_label.setMinimumHeight(150)  # 画像の収まりが良い高さ
        self.preview_label.setStyleSheet("border: 1px solid #444; background: #222;")
        # アスペクト比を維持して拡大縮小させる設定
        self.preview_label.setScaledContents(False)

        left_layout.addWidget(self.preview_label, stretch=1)

        layout.addWidget(left_group, stretch=1)

    def setup_mappings(self, layout):
        right_group = QGroupBox("fontconfig マッピング (カテゴリ別)")
        right_main_layout = QVBoxLayout(right_group)

        self.tabs = QTabWidget()
        self.combos = {}

        for group in ALLOW_MAPPING_CATEGORY:
            tab_page = QWidget()
            tab_v_layout = QVBoxLayout(tab_page)  # 一括ボタンを上に置くためVBox

            # --- カテゴリごとの説明や注意書きを追加 ---
            warning_infolabel_style = "color: #856404; background-color: #fff3cd; border: 1px solid #ffeeba; padding: 5px; border-radius: 3px;"
            normal_infolabel_style = "color: #4a5568; background-color: #edf2f7; border: 1px solid #cbd5e0; padding: 8px; border-radius: 5px;"
            if group == "special":
                info_label = QLabel(
                    "⚠️ <b>注意:</b> このカテゴリは通常、変更する必要はありません。"
                )
                info_label.setStyleSheet(warning_infolabel_style)
                info_label.setWordWrap(True)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "console":
                info_label = QLabel("コンソールウィンドウで使用されるフォントです。")
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "every":
                info_label = QLabel("UI全般で使用されるフォントです。")
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "book":
                info_label = QLabel("本で使用されるフォントです。")
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "handwrite":
                info_label = QLabel("手紙、メモで使用されるフォントです。")
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "mcm":
                info_label = QLabel(
                    "JapaneseFontLibraryのMCMフォントマップパッチ適用状態で使用されるフォントです。"
                )
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "custom":
                info_label = QLabel(
                    "独自に追加されたマップです。<br>"
                    "プリセットファイル(presets\プリセット名.yml)の mappings に、category: custom で追加登録することで表示されます。"
                )
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)

            # --- グループ一括ボタン ---
            btn_apply_all = QPushButton(
                f"左のリストで選択中のフォントを {group} 全体に適用"
            )
            btn_apply_all.clicked.connect(
                lambda _, g=group: self.on_apply_font_to_group(g)
            )
            tab_v_layout.addWidget(btn_apply_all)

            # --- 各マッピング行 ---
            form_widget = QWidget()
            tab_layout = QFormLayout(form_widget)

            group_mappings = [m for m in self.preset.mappings if m["category"] == group]
            for m in group_mappings:
                map_name = m["map_name"]

                # 行全体を管理するレイアウト
                row_layout = QHBoxLayout()

                # 1. 適用ボタン 「>>」 (左端)
                btn_apply = QPushButton(">>")
                btn_apply.setFixedWidth(35)  # さらにコンパクトに
                btn_apply.setToolTip("選択中のフォントをここに適用")
                btn_apply.clicked.connect(
                    lambda _, n=map_name: self.on_apply_selected_to_row(n)
                )

                # 2. マップ名ラベル
                label = QLabel(map_name)
                label.setMinimumWidth(150)  # ラベルの開始位置を揃えて綺麗に見せる

                # 3. コンボボックス (右端)
                combo = QComboBox()
                combo.setObjectName(map_name)
                combo.currentIndexChanged.connect(
                    lambda _, n=map_name, c=combo: self.on_mapping_changed(
                        n, c.currentData()
                    )
                )
                self.combos[map_name] = combo

                # レイアウトに詰め込む
                row_layout.addWidget(btn_apply)
                row_layout.addWidget(label)
                row_layout.addWidget(combo, stretch=1)

                # QFormLayout の代わりに QVBoxLayout などで縦に積んでいくか、
                # QFormLayout のaddRow(row_layout) を使う
                tab_layout.addRow(row_layout)

            tab_v_layout.addWidget(form_widget)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(tab_page)
            self.tabs.addTab(scroll, group.capitalize())

        right_main_layout.addWidget(self.tabs)
        layout.addWidget(right_group, stretch=2)

    # --- アクション用メソッド ---
    def on_apply_selected_to_row(self, map_name: str):
        """左のリストで選択されているフォント名を、指定した行のコンボボックスにセットする"""
        selected_item = self.list_widget_font_names.currentItem()
        if selected_item:
            item_text = selected_item.text()
            # SWFファイル名の行は無視
            if item_text.startswith(SWF_FILE_LINE_PREFIX):
                QMessageBox.information(
                    self,
                    "選択エラー",
                    "SWFファイル名ではなく、フォント名を選択してください。",
                )
                return
            # フォント名から接頭辞を除去
            font_name = item_text.lstrip(FONT_NAME_LINE_PREFIX).strip()
            swf_path = selected_item.data(Qt.UserRole)
            combo = self.combos.get(map_name)
            if combo:
                if swf_path:
                    self._pending_mapping_swf_paths[map_name] = str(swf_path)
                # findTextで見つからない（Dragon_script等）場合も考慮して
                idx = combo.findData(font_name)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                else:
                    # 暫定的に追加して選択
                    combo.addItem(
                        self.format_mapping_font_label(font_name, str(swf_path or "")),
                        font_name,
                    )
                    combo.setCurrentIndex(combo.findData(font_name))

    def on_apply_font_to_group(self, group_name: str):
        """左のリストで選択されているフォント名を、グループ内の全ての行に適用する"""
        selected_item = self.list_widget_font_names.currentItem()
        if not selected_item:
            return

        item_text = selected_item.text()
        # SWFファイル名の行は無視
        if item_text.startswith(SWF_FILE_LINE_PREFIX):
            QMessageBox.information(
                self,
                "選択エラー",
                "SWFファイル名ではなく、フォント名を選択してください。",
            )
            return

        group_mappings = [
            m for m in self.preset.mappings if m["category"] == group_name
        ]

        for m in group_mappings:
            self.on_apply_selected_to_row(m["map_name"])

    def refresh_ui_from_scan_results(self):
        """現在のスキャン結果をUIに反映する"""
        if not self.settings.swf_dir:
            self.list_widget_font_names.clear()
            return

        if not self.scanned_swf_entries or not isinstance(
            self.scanned_swf_entries, list
        ):
            self.list_widget_font_names.clear()
            return

        # SWFファイル名ごとにフォント名をグループ化
        swf_to_fonts = {}
        all_fonts = []

        for entry in self.scanned_swf_entries:
            if not isinstance(entry, dict):
                continue
            swf_path_str = entry.get("swf_path", "")
            if not swf_path_str:
                continue

            try:
                swf_abs_path = self.controller.resolve_absolute_swf_path(swf_path_str)
                swf_display_path = self.controller.to_relative_swf_path(swf_abs_path)
            except Exception:
                swf_display_path = Path(swf_path_str).name

            if swf_display_path not in swf_to_fonts:
                swf_to_fonts[swf_display_path] = {
                    "fonts": [],
                    "swf_path": swf_path_str,
                }

            # 【データ構造の柔軟な吸収】font_names (リスト) と font_name (文字列) の両方に対応
            fonts = entry.get("font_names", [entry.get("font_name")])
            # Noneを除去してリスト化
            if not isinstance(fonts, list):
                fonts = [fonts] if fonts else []
            fonts = [f for f in fonts if f]

            for font_name in fonts:
                if font_name not in swf_to_fonts[swf_display_path]["fonts"]:
                    swf_to_fonts[swf_display_path]["fonts"].append(font_name)
                if font_name not in all_fonts:
                    all_fonts.append(font_name)

        # UI反映: 階層構造で表示
        self.list_widget_font_names.clear()
        for swf_display_path in sorted(swf_to_fonts.keys()):
            # SWFファイル名を追加（選択不可）
            swf_item = QListWidgetItem(f"{SWF_FILE_LINE_PREFIX}{swf_display_path}")
            swf_item.setFlags(Qt.NoItemFlags)  # 選択不可
            self.list_widget_font_names.addItem(swf_item)

            # フォント名を追加（インデント表示）
            for font_name in sorted(swf_to_fonts[swf_display_path]["fonts"]):
                font_item = QListWidgetItem(f"{FONT_NAME_LINE_PREFIX}{font_name}")
                font_item.setData(
                    Qt.UserRole,
                    swf_to_fonts[swf_display_path]["swf_path"],
                )
                self.list_widget_font_names.addItem(font_item)

        # コンボボックスの更新には全フォント名のフラットリストを渡す
        self.update_combos_with_detected(sorted(all_fonts))

        # 検索フィルターを再適用
        self.apply_font_list_filter(self.lineedit_font_search.text())

    def on_font_search_text_changed(self, text: str):
        """フォント名検索の入力変更時にリストを絞り込む"""
        self.apply_font_list_filter(text)

    def apply_font_list_filter(self, search_text: str):
        """フォント名リストを検索文字列でフィルタする。"""
        keyword = (search_text or "").strip().lower()

        current_swf_item = None
        current_swf_name = ""
        current_swf_name_matches = False
        current_swf_has_visible_font = False

        for i in range(self.list_widget_font_names.count()):
            item = self.list_widget_font_names.item(i)
            item_text = item.text()

            if item_text.startswith(SWF_FILE_LINE_PREFIX):
                if current_swf_item is not None:
                    if keyword:
                        current_swf_item.setHidden(not current_swf_has_visible_font)
                    else:
                        current_swf_item.setHidden(False)

                current_swf_item = item
                current_swf_name = item_text[len(SWF_FILE_LINE_PREFIX) :].strip()
                current_swf_name_matches = (not keyword) or (
                    keyword in current_swf_name.lower()
                )
                current_swf_has_visible_font = False
                item.setHidden(False)
                continue

            font_name = item_text
            if item_text.startswith(FONT_NAME_LINE_PREFIX):
                font_name = item_text[len(FONT_NAME_LINE_PREFIX) :].strip()

            is_match = (
                (not keyword)
                or current_swf_name_matches
                or (keyword in font_name.lower())
            )
            item.setHidden(not is_match)
            if is_match:
                current_swf_has_visible_font = True

        if current_swf_item is not None:
            if keyword:
                current_swf_item.setHidden(not current_swf_has_visible_font)
            else:
                current_swf_item.setHidden(False)

    def on_font_selection_changed(self):
        """リストで選択されたフォントのプレビュー画像を表示する"""
        selected_item = self.list_widget_font_names.currentItem()
        if not selected_item:
            self.current_preview_image_path = None
            self.preview_label.setText("No selection")
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setCursor(Qt.ArrowCursor)
            return

        item_text = selected_item.text()

        # SWFファイル名の行が選択された場合は何もしない
        if item_text.startswith(SWF_FILE_LINE_PREFIX):
            self.current_preview_image_path = None
            self.preview_label.setText("SWFファイルが選択されています")
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setCursor(Qt.ArrowCursor)
            return

        # フォント名から接頭辞を除去
        font_name = item_text
        if item_text.startswith(FONT_NAME_LINE_PREFIX):
            font_name = item_text[len(FONT_NAME_LINE_PREFIX) :].strip()

        # 1. 選択項目のSWFパスを取得
        swf_path_str = selected_item.data(Qt.UserRole)
        if not swf_path_str:
            self.current_preview_image_path = None
            self.preview_label.setText(f"SWFファイルが見つかりません\n{font_name}")
            self.preview_label.setCursor(Qt.ArrowCursor)
            return

        try:
            found_swf_path = self.controller.resolve_absolute_swf_path(swf_path_str)
        except Exception:
            self.current_preview_image_path = None
            self.preview_label.setText(f"SWFファイルが見つかりません\n{font_name}")
            self.preview_label.setCursor(Qt.ArrowCursor)
            return

        if not found_swf_path:
            self.current_preview_image_path = None
            self.preview_label.setText(f"SWFファイルが見つかりません\n{font_name}")
            self.preview_label.setCursor(Qt.ArrowCursor)
            return

        # 2. プレビュー画像を探す
        img_path = find_preview_image(
            found_swf_path,
            font_name=font_name,
            debug=self.debug,
        )

        if img_path and img_path.exists():
            self.current_preview_image_path = img_path
            pixmap = QPixmap(str(img_path))
            # ラベルのサイズに合わせてリサイズ（アスペクト比維持）
            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
            self.preview_label.setText("")  # テキストを消す
            self.preview_label.setCursor(Qt.PointingHandCursor)
        else:
            self.current_preview_image_path = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"プレビュー画像が見つかりません\n{font_name}")
            self.preview_label.setCursor(Qt.ArrowCursor)

    def on_preview_label_clicked(self):
        """プレビュー画像をクリックした時に、拡大表示ダイアログを開く。"""
        if not self.current_preview_image_path:
            return
        if not self.current_preview_image_path.exists():
            return

        dialog = PreviewImageDialog(self.current_preview_image_path, self)
        dialog.exec()

    def update_combos_with_detected(self, detected):
        """コンボボックスの中身を更新する"""
        for map_name, combo in self.combos.items():
            # 現在 YAML に保存されている値を取得
            current_val = self.preset.get_mapping_font_name(map_name)

            combo.blockSignals(True)
            combo.clear()
            combo.addItem(UNDEFINE_FONT_NAME, "")

            # 【ここがポイント！】
            # 「今回見つかったフォント」 ＋ 「現在設定されているフォント」
            # を合体させてリストを作る
            all_items = set(detected)
            if current_val:
                all_items.add(current_val)

            items = sorted(list(all_items))
            for f in items:
                combo.addItem(self.format_mapping_font_label(f), f)

            # 値を再セット（これでスキャン前でも名前が消えない！）
            idx = combo.findData(current_val if current_val else "")
            if idx >= 0:
                combo.setCurrentIndex(idx)

            combo.blockSignals(False)

    def on_preset_save_as_clicked(self):
        """新しい名前でプリセットを複製保存"""
        new_preset_name, ok = QInputDialog.getText(
            self,
            "プリセットの別名保存",
            "プリセット名を入力してください:",
            QLineEdit.Normal,
        )

        if ok and new_preset_name.strip():
            # ファイル名の正規化
            new_preset_name = new_preset_name.strip()
            new_preset_name_norm = (
                new_preset_name
                if new_preset_name.lower().endswith(".yml")
                else f"{new_preset_name}.yml"
            )
            new_preset_path = PRESETS_DIR / new_preset_name_norm

            if new_preset_path.exists():
                reply = QMessageBox.warning(
                    self,
                    "上書き確認",
                    f"'{new_preset_name_norm}' は既に存在します。上書きしますか？",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return

            # 保存して切り替え
            self.preset.preset_path = new_preset_path
            self.preset.save()

            # 設定クラスの属性に保存 (プロパティ経由を想定)
            self.settings.last_preset = str(new_preset_name_norm)
            self.settings.save()

            # UIの更新
            self.refresh_preset_list()
            # リスト更新後に新しい項目を選択（シグナルが発生して load が走る）
            self.preset_combo.setCurrentText(new_preset_path.stem)

            QMessageBox.information(
                self, "完了", f"プリセット '{new_preset_name}' を作成しました。"
            )

    def on_reload_preset_clicked(self):
        """現在のプリセットファイルを再読み込みする"""
        if self.preset_is_dirty:
            reply = QMessageBox.question(
                self,
                "保存の確認",
                "変更が保存されていません。再読み込み前に保存しますか？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self.on_save_current_preset_clicked()
                if self.preset_is_dirty:
                    return
            elif reply == QMessageBox.Cancel:
                return

        self.preset.load()
        self.refresh_ui_from_config()

    def on_preset_changed(self, preset_name):
        if not preset_name:
            return

        # 現在のパスと同じなら何もしない
        new_path = PRESETS_DIR / f"{preset_name}.yml"
        if self.preset.preset_path == new_path:
            return

        # 切り替え前に保存確認
        if self.preset_is_dirty:
            reply = QMessageBox.question(
                self,
                "保存の確認",
                "変更が保存されていません。切り替える前に保存しますか？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if reply == QMessageBox.Yes:
                self.on_save_current_preset_clicked()
            elif reply == QMessageBox.Cancel:
                # 選択を元に戻す（再帰呼び出しを防ぐため一時的に遮断）
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentText(self.preset.preset_path.stem)
                self.preset_combo.blockSignals(False)
                return

        if new_path.exists():
            self.preset.preset_path = new_path
            self.preset.load()

            # settings.settings ではなくインスタンス属性に合わせる
            self.settings.last_preset = str(new_path)
            self.settings.save()

            self.refresh_ui_from_config()
            # ここでDirtyフラグがリセットされる（refresh_ui_from_config内）

    def on_mapping_changed(self, map_name, font_name):
        """設定値のメモリ上更新のみ行う"""
        # コンボボックスが空（リスト更新中など）の時は、メモリ上の設定を書き換えない
        if font_name is None:
            return
        new_font = font_name
        selected_swf_path = self._pending_mapping_swf_paths.pop(map_name, None)
        if new_font and not selected_swf_path:
            selected_swf_path = self.find_swf_path_for_font(new_font)

        try:
            changed = self.controller.update_mapping_from_ui(
                map_name=map_name,
                font_name=new_font,
                selected_swf_path=selected_swf_path,
                save=False,
            )
        except ValueError as e:
            QMessageBox.warning(self, "入力エラー", str(e))
            return

        if changed:
            self.preset_is_dirty = True
            # タイトルに * をつけて「未保存」を視覚化
            self.setWindowTitle(f"{MAIN_WINDOW_TITLE} *")
        # self.config.save() はここでは呼ばない！

    def find_swf_path_for_font(self, font_name: str) -> str:
        """現在のスキャン結果からフォント名に対応するSWFパスを返す"""
        for entry in self.scanned_swf_entries:
            if not isinstance(entry, dict):
                continue
            fonts = entry.get("font_names", [])
            if not isinstance(fonts, list):
                continue
            if font_name in fonts:
                return str(entry.get("swf_path", ""))
        return ""

    def format_mapping_font_label(self, font_name: str, swf_path: str = "") -> str:
        """マッピング表示用ラベルを生成する（フォント名 + SWFファイル）。"""
        if not font_name:
            return ""

        found_swf_path = swf_path or self.find_swf_path_for_font(font_name)
        if not found_swf_path:
            return font_name

        try:
            swf_abs = self.controller.resolve_absolute_swf_path(found_swf_path)
            swf_display = self.controller.to_relative_swf_path(swf_abs)
        except Exception:
            swf_display = Path(found_swf_path).name

        return f"{font_name} ({swf_display})"

    def setup_validnamechars_input(self, layout):
        """validNameChars入力レイアウトのセットアップ"""
        hboxlayout_validnamechars = QHBoxLayout()

        label_validnamechars = QLabel("キャラ名に使用できる文字:")
        self.lineedit_validnamechars = QLineEdit()
        self.lineedit_validnamechars.setText(self.preset.validnamechars)
        self.lineedit_validnamechars.textChanged.connect(self.on_validnamechars_changed)

        hboxlayout_validnamechars.addWidget(label_validnamechars)
        hboxlayout_validnamechars.addWidget(self.lineedit_validnamechars, stretch=1)

        # レイアウトに組み立てた部品を挿入
        layout.addLayout(hboxlayout_validnamechars)

    def on_validnamechars_changed(self, text):
        """validNameCharsが変更されたときのアクション"""
        # もともとプリセットに記録されている内容から変更されていれば、
        # プリセットの内容を更新した上で変更フラグを立てる。
        if self.preset.validnamechars != text:
            self.preset.validnamechars = text
            self.preset_is_dirty = True
            # ウィンドウタイトルに「 *」を付ける事で、「何か変更したよ」というのを視覚的に通知している。
            self.setWindowTitle(f"{MAIN_WINDOW_TITLE} *")

    def on_generate_clicked(self):
        # バリデーション（必須項目）
        missing = self.controller.validate_required_mappings()
        if missing:
            error_msg = (
                "以下の必須項目が設定されていません。フォントを選択してください：\n\n"
                + "\n".join([f"・{m}" for m in missing])
            )
            QMessageBox.warning(self, "入力チェック", error_msg)
            return

        # バリデーション（現在のフォント一覧に存在するか）
        # 階層構造からフォント名のみを抽出
        available_fonts = set()
        for i in range(self.list_widget_font_names.count()):
            item_text = self.list_widget_font_names.item(i).text()
            # SWFファイル名の行は除外
            if not item_text.startswith(SWF_FILE_LINE_PREFIX):
                # フォント名から接頭辞を除去
                font_name = item_text.lstrip(FONT_NAME_LINE_PREFIX).strip()
                available_fonts.add(font_name)

        not_found = self.controller.find_missing_fonts(available_fonts)
        if not_found:
            dprint(
                "\n設定されたフォントが現在のSWFフォルダ内に見つかりません:",
                self.debug,
            )
            for map_name, f in not_found:
                dprint(f"  ・{map_name}: {f}", self.debug)
            warning_msg = (
                "以下の設定済みフォントマップにて、紐づくフォントSWFが存在しません。\n"
                "そのまま出力しますか？（UI全体が豆腐化する可能性があります）\n\n"
                + "\n".join([f"・{m}: {n}" for m, n in not_found])
            )
            reply = QMessageBox.warning(
                self,
                "フォント未検出",
                warning_msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        # 出力先選択
        initial_dir = str(self.settings.output_dir) if self.settings.output_dir else "."
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "ユーザープリセットの出力先フォルダを選択してください",
            initial_dir,
        )
        if not selected_dir:
            dprint("出力がキャンセルされました。", self.debug)
            return

        self.settings.output_dir = selected_dir
        self.settings.save()

        # 実行はコントローラに委譲
        try:
            # フォント指定が空の場合の補完判定
            selected_fonts = {
                m["font_name"]
                for m in self.preset.mappings
                if m.get("font_name") and m.get("font_name") != ""
            }

            use_fallback = False
            if not selected_fonts:
                # コアフォントの存在確認
                from pathlib import Path as PathlibPath

                core_swf = (
                    PathlibPath(__file__).parent.parent.parent
                    / "data"
                    / "fonts_core.swf"
                )
                if core_swf.exists():
                    use_fallback = True
                    dprint(
                        "⚠️ フォント指定が空のため、fonts_core.swf を使用して補完します。",
                        self.debug,
                    )
                else:
                    QMessageBox.critical(
                        self,
                        "エラー",
                        "フォントが指定されておらず、標準フォント(fonts_core.swf)も見つかりません。",
                    )
                    return

            out_file = self.controller.generate_preset(Path(selected_dir), use_fallback)
            dprint(f"✅ 生成成功: {out_file}", self.debug)

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("完了")
            message = f"生成が完了しました！\n\n出力先:\n{out_file.parent}"
            if use_fallback:
                message = (
                    "フォントが指定されていなかったため、標準の fonts_core.swf を使用して書き出しました。\n\n"
                    + message
                )
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Information)
            open_folder_btn = msg_box.addButton("出力先を開く", QMessageBox.ActionRole)
            msg_box.addButton("閉じる", QMessageBox.AcceptRole)
            msg_box.exec()
            if msg_box.clickedButton() == open_folder_btn:
                os.startfile(out_file.parent)
        except Exception as e:
            print(f"❌ 生成失敗: {e}")
            QMessageBox.critical(self, "エラー", f"生成中にエラーが発生しました:\n{e}")

    def on_save_current_preset_clicked(self):
        """現在のメモリ上の設定をファイルに書き出す"""
        # 必須項目が一つも埋まっていない、などの極端な状態なら警告
        filled_count = sum(1 for m in self.preset.mappings if m.get("font_name"))
        if filled_count == 0:
            reply = QMessageBox.warning(
                self,
                "保存の確認",
                "現在、全てのフォント設定が空ですが、このまま保存しますか？\n(既存の設定が消える可能性があります)",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return
        try:
            self.controller.save_preset()
            self.preset_is_dirty = False
            # タイトルの * を消す
            self.setWindowTitle(MAIN_WINDOW_TITLE)
            dprint("✅ ユーザープリセットを保存しました。", self.debug)
        except Exception as e:
            QMessageBox.critical(self, "保存エラー", f"設定の保存に失敗しました:\n{e}")

    def closeEvent(self, event):
        """閉じる時の保存確認"""

        if self.preset_is_dirty:
            reply = QMessageBox.question(
                self,
                "保存の確認",
                "変更が保存されていません。保存してから閉じますか？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )

            if reply == QMessageBox.Yes:
                self.on_save_current_preset_clicked()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()  # キャンセル
        else:
            event.accept()

    def check_environment(self):
        """環境チェック"""
        # FFDecが存在するか
        # if not Path(self.settings.ffdec_cli).exists():
        #     QMessageBox.critical(
        #         self,
        #         "環境エラー",
        #         f"FFDecが見つかりません。\nパスを確認してください:\n{self.settings.ffdec_cli}",
        #     )
        #     return False
        # もしほかにチェックを挟みたくなった時用にのこしておく。
        return True


def run_app(app: QApplication = None, debug: bool = False):
    """アプリケーションを起動するユーティリティ。

    `main.py` から起動処理を委譲するために、設定・プリセット・キャッシュの読み込み
    とウィンドウ生成をここで行う。
    """
    from pathlib import Path

    if app is None:
        from PySide6.QtWidgets import QApplication

        app = QApplication([])

    # 1. システム設定を読み込み
    settings = Settings(Path(SETTINGS_FILE))
    settings.load()
    if settings.migrated:
        dprint(
            "システム設定データのマイグレーションが完了しました。必要に応じて内容を確認して保存してください。",
            debug,
        )

    # settings.yml に swf_dir がある場合、存在しなければ未設定に戻す
    if settings.swf_dir:
        swf_dir = Path(settings.swf_dir)
        if not swf_dir.exists() or not swf_dir.is_dir():
            dprint(
                f"settings.yml の swf_dir が無効なため未設定に戻します: {swf_dir}",
                debug,
            )
            settings.swf_dir = ""
            settings.save()

    # 1.5. 起動前にプリセット存在を保証（0件なら default.yml を作成）
    try:
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        preset_files = list(PRESETS_DIR.glob("*.yml"))
        if not preset_files:
            default_preset_path = PRESETS_DIR / "default.yml"
            Preset(default_preset_path).save()
            settings.last_preset = default_preset_path.name
            settings.save()
            dprint(
                f"プリセットが存在しなかったため、デフォルトプリセットを作成しました: {default_preset_path}",
                debug,
            )
    except Exception as e:
        print(f"デフォルトプリセットの初期化に失敗しました: {e}")

    # 手順1: Settings の健全化 — 欠けている設定をプリセットの生データから吸い上げる
    try:
        updated = False
        if PRESETS_DIR.exists():
            for pfile in PRESETS_DIR.glob("*.yml"):
                try:
                    with open(pfile, "r", encoding=ENCODE) as f:
                        pdata = yaml.safe_load(f) or {}
                    # 例: 共通の swf_dir, output_dir が settings に存在しなければ吸い上げる
                    if not settings.swf_dir and pdata.get("swf_dir"):
                        settings.swf_dir = pdata.get("swf_dir")
                        updated = True
                    if not settings.output_dir and pdata.get("output_dir"):
                        settings.output_dir = pdata.get("output_dir")
                        updated = True
                    # mappings 内の swf_path / output_path を参照して設定へ吸い上げ
                    if "mappings" in pdata:
                        for m in pdata.get("mappings", []):
                            try:
                                # swf_path は相対パスであることが多いが、もしパス区切りを含む場合は親ディレクトリを採用
                                sp = m.get("swf_path")
                                if sp and not settings.swf_dir:
                                    sp_str = str(sp)
                                    if (
                                        ("/" in sp_str)
                                        or ("\\" in sp_str)
                                        or Path(sp_str).is_absolute()
                                    ):
                                        settings.swf_dir = str(Path(sp_str).parent)
                                        updated = True
                                        # 一度見つかれば十分
                                        break
                                op = m.get("output_path")
                                if op and not settings.output_dir:
                                    settings.output_dir = op
                                    updated = True
                                    break
                            except Exception:
                                # 走査中の個別エラーは無視して次へ
                                continue
                    if updated:
                        dprint(
                            f"システム設定をプリセットで補間しました: {pfile}", debug
                        )
                        # もし十分な値が見つかれば早期終了して保存しても良い
                        # ただしここでは全ファイルを走査して可能な限り吸い上げる
                except Exception as e:
                    print(f"プリセット読み込み中にエラー: {pfile}: {e}")
        if updated:
            try:
                settings.save()
                dprint("システム設定を更新して保存しました。", debug)
            except Exception as e:
                print(f"システム設定の保存に失敗しました: {e}")
    except Exception as e:
        print(f"システム設定の健全化中にエラーが発生しました: {e}")

    # 手順2: Presets の一括マイグレート（テンプレート補完等）
    try:
        if PRESETS_DIR.exists():
            # print("全プリセットをマイグレートします...")
            for pfile in PRESETS_DIR.glob("*.yml"):
                pr = None
                try:
                    # print(f"マイグレート中: {pfile}")
                    pr = Preset(pfile)
                    pr.load()
                    pr.save()
                except Exception as e:
                    print(f"プリセットのマイグレートに失敗しました: {pfile}: {e}")
                if pr and getattr(pr, "migrated", False):
                    dprint(
                        f"マイグレートが完了しました。必要に応じて内容を確認して保存してください。: {pfile}",
                        debug,
                    )
    except Exception as e:
        print(f"プリセット一括マイグレート中にエラーが発生しました: {e}")

    # 2. どのプリセットを使うか決定
    last_preset_name = settings.last_preset
    candidate_path = None
    if last_preset_name:
        candidate_path = PRESETS_DIR / last_preset_name
    if candidate_path is not None and candidate_path.exists():
        preset_path = candidate_path
    else:
        preset_path = DEFAULT_PRESET_FILE

    # 3. プリセットとキャッシュを読み込み
    preset = Preset(preset_path)
    cache = Cache(Path(CACHE_FILE))

    # 4. ウィンドウを生成して表示
    window = MainWindow(settings=settings, preset=preset, cache=cache, debug=debug)
    if window.startup_aborted:
        return 1
    window.show()

    return app.exec()

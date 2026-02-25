import os
from pathlib import Path

import yaml
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
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
    ENCODE,
    MAIN_WINDOW_TITLE,
    PRESETS_DIR,
    SETTINGS_FILE,
)
from models.cache import Cache
from models.preset import Preset
from models.settings import Settings
from src.gui.main_controller import MainController
from src.modules.find_preview_image import find_preview_image


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, preset: Preset, cache: Cache):
        super().__init__()
        self.settings = settings
        self.preset = preset
        self.cache = cache
        self.controller = MainController(settings=settings, preset=preset, cache=cache)
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
        # 起動時の重い処理は `run_app()` 側で行うため、ここでは何もしない
        return

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
        dir_path = QFileDialog.getExistingDirectory(
            self, "フォントSWFが含まれるフォルダを選択"
        )
        if dir_path:
            p = Path(dir_path)
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
            self.refresh_font_names_list(swf_dir)
            # QMessageBox.information(self, "完了", "フォルダの内容を読み込みました。")
        else:
            QMessageBox.warning(self, "エラー", "フォルダが見つかりません。")

    def refresh_font_names_list(self, swf_dir_path: Path):
        """フォント名一覧を更新する"""
        # フォント名一覧更新処理中ダイアログを表示する。
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
            # コントローラに実際のスキャン処理を委譲
            font_list = self.controller.scan_swf_directory(swf_dir_path, debug=False)

            # UI の更新はここで行う
            self.list_widget_font_names.clear()
            self.list_widget_font_names.addItems(font_list)
            self.update_combos_with_detected(font_list)

        except Exception as e:
            msg = "フォント名一覧の更新中にエラーが発生しました:"
            print(f"{msg} {e}")
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

        # 2. 別名保存ボタン
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
            if font_name and combo.findText(font_name) == -1:
                combo.addItem(font_name, font_name)
            combo.setCurrentText(font_name if font_name else "-- 選択なし --")
            combo.blockSignals(False)

        # 未保存フラグをリセット
        self.preset_is_dirty = False
        self.setWindowTitle(MAIN_WINDOW_TITLE)

    def setup_font_names(self, layout):
        left_group = QGroupBox("フォルダ内に存在するフォント名")
        left_layout = QVBoxLayout(left_group)

        # フォントリスト
        self.list_widget_font_names = QListWidget()
        # 項目が選択されたらプレビューを更新するシグナルを接続
        self.list_widget_font_names.itemSelectionChanged.connect(
            self.on_font_selection_changed
        )
        left_layout.addWidget(self.list_widget_font_names, stretch=2)

        # ★プレビュー画像表示エリア
        self.preview_label = QLabel("プレビュー")
        self.preview_label.setAlignment(Qt.AlignCenter)

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
                    "⚠️ <b>注意:</b> このカテゴリは通常、変更する必要はありません。<br>"
                    "バニラの特殊フォント（ドラゴン文字等）を維持することを推奨します。"
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
                combo.currentTextChanged.connect(
                    lambda text, n=map_name: self.on_mapping_changed(n, text)
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
            font_name = selected_item.text()
            combo = self.combos.get(map_name)
            if combo:
                # findTextで見つからない（Dragon_script等）場合も考慮して
                idx = combo.findText(font_name)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                else:
                    # 暫定的に追加して選択
                    combo.addItem(font_name, font_name)
                    combo.setCurrentText(font_name)

    def on_apply_font_to_group(self, group_name: str):
        """左のリストで選択されているフォント名を、グループ内の全ての行に適用する"""
        selected_item = self.list_widget_font_names.currentItem()
        if not selected_item:
            return

        font_name = selected_item.text()
        group_mappings = [
            m for m in self.preset.mappings if m["category"] == group_name
        ]

        for m in group_mappings:
            self.on_apply_selected_to_row(m["map_name"])

    def refresh_ui_from_cache(self):
        """スキャンを行わず、現在のフォルダ配下のキャッシュデータのみをUIに反映する"""
        if not self.settings.swf_dir:
            self.list_widget_font_names.clear()
            return

        # 比較用に Path オブジェクト化
        current_swf_dir = Path(self.settings.swf_dir).resolve()

        detected = set()
        for entry in self.cache.data:
            swf_path_str = entry.get("swf_path", "")
            if not swf_path_str:
                continue

            # キャッシュのパスを正規化
            swf_path = Path(swf_path_str).resolve()

            # ★修正ポイント：Pathの機能で「現在のフォルダ配下か」を判定
            # python 3.9+ なら is_relative_to が使えます
            try:
                if swf_path.is_relative_to(current_swf_dir):
                    for f in entry.get("font_names", []):
                        detected.add(f)
            except ValueError:
                # 異なるドライブなどの理由で相対関係にない場合はここに来る
                continue

        sorted_fonts = sorted(list(detected))

        # UI反映
        self.list_widget_font_names.clear()
        self.list_widget_font_names.addItems(sorted_fonts)
        self.update_combos_with_detected(sorted_fonts)

    def on_font_selection_changed(self):
        """リストで選択されたフォントのプレビュー画像を表示する"""
        selected_item = self.list_widget_font_names.currentItem()
        if not selected_item:
            self.preview_label.setText("No selection")
            self.preview_label.setPixmap(QPixmap())  # クリア
            return

        font_name = selected_item.text()

        # 1. キャッシュからこのフォント名を持つ SWF パスを探す
        found_swf_path = None
        swf_dir = Path(self.settings.swf_dir) if self.settings.swf_dir else None
        if not swf_dir:
            self.preview_label.setText("SWF dir not set")
            return
        for entry in self.cache.data:
            if font_name in entry.get("font_names", []):
                # 保存されている相対パスを絶対パスに戻す
                found_swf_path = swf_dir / entry["swf_path"]
                break

        if not found_swf_path:
            self.preview_label.setText("SWF not found")
            return

        # 2. 前のステップで作った find_preview_image を呼び出す
        # (modules.utils 等に切り出している想定)
        img_path = find_preview_image(found_swf_path)

        if img_path and img_path.exists():
            pixmap = QPixmap(str(img_path))
            # ラベルのサイズに合わせてリサイズ（アスペクト比維持）
            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
            self.preview_label.setText("")  # テキストを消す
        else:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"プレビュー画像が見つかりません\n{font_name}")

    def update_combos_with_detected(self, detected):
        """コンボボックスの中身を更新する"""
        for map_name, combo in self.combos.items():
            # 現在 YAML に保存されている値を取得
            current_val = self.preset.get_mapping_font_name(map_name)

            combo.blockSignals(True)
            combo.clear()
            combo.addItem("-- 選択なし --", "")

            # 【ここがポイント！】
            # 「今回見つかったフォント」 ＋ 「現在設定されているフォント」
            # を合体させてリストを作る
            all_items = set(detected)
            if current_val:
                all_items.add(current_val)

            items = sorted(list(all_items))
            for f in items:
                combo.addItem(f, f)

            # 値を再セット（これでスキャン前でも名前が消えない！）
            idx = combo.findText(current_val)
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
        if font_name == "" or font_name is None:
            return
        new_font = "" if font_name == "-- 選択なし --" else font_name
        for m in self.preset.mappings:
            if m["map_name"] == map_name:
                # 値が本当に変わった時だけ Dirty フラグを立てる
                if m["font_name"] != new_font:
                    m["font_name"] = new_font
                    self.preset_is_dirty = True
                    # タイトルに * をつけて「未保存」を視覚化
                    self.setWindowTitle(f"{MAIN_WINDOW_TITLE} *")
                break
        # self.config.save() はここでは呼ばない！

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
        available_fonts = {
            self.list_widget_font_names.item(i).text()
            for i in range(self.list_widget_font_names.count())
        }
        not_found = self.controller.find_missing_fonts(available_fonts)
        if not_found:
            print("\n⚠️ [WARNING] 設定されたフォントが現在のフォルダ内に見つかりません:")
            for map_name, f in not_found:
                print(f"  ・{map_name}: {f}")
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
            print("出力がキャンセルされました。")
            return

        self.settings.output_dir = selected_dir
        self.settings.save()

        # 実行はコントローラに委譲
        try:
            out_file = self.controller.generate_preset(Path(selected_dir))
            print(f"✅ 生成成功: {out_file}")
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("完了")
            msg_box.setText(f"生成が完了しました！\n\n出力先:\n{out_file.parent}")
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
            print("✅ ユーザープリセットを保存しました。")
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


def run_app(app=None):
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
                        print(f"settings に値を吸い上げました: {pfile}")
                        # もし十分な値が見つかれば早期終了して保存しても良い
                        # ただしここでは全ファイルを走査して可能な限り吸い上げる
                except Exception as e:
                    print(f"プリセット読み込み中にエラー: {pfile}: {e}")
        if updated:
            try:
                settings.save()
                print("Settings を更新して保存しました。")
            except Exception as e:
                print(f"Settings の保存に失敗しました: {e}")
    except Exception as e:
        print(f"Settings 健全化中にエラーが発生しました: {e}")

    # 手順2: Presets の一括マイグレート（テンプレート補完等）
    try:
        if PRESETS_DIR.exists():
            print("全プリセットをマイグレートします...")
            for pfile in PRESETS_DIR.glob("*.yml"):
                try:
                    print(f"マイグレート中: {pfile}")
                    pr = Preset(pfile)
                    pr.load()
                    pr.save()
                except Exception as e:
                    print(f"プリセットのマイグレートに失敗しました: {pfile}: {e}")
            print("プリセットのマイグレートが完了しました。")
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
        preset_path = Path(PRESETS_DIR) / "default.yml"

    # 3. プリセットとキャッシュを読み込み
    preset = Preset(preset_path)
    cache = Cache(Path(CACHE_FILE))

    # 4. ウィンドウを生成して表示
    window = MainWindow(settings=settings, preset=preset, cache=cache)
    window.show()

    return app.exec()

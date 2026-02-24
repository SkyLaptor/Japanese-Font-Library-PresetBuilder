import os
from pathlib import Path

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

from const import BASE_GROUP, PRESETS_DIR, PROGRAM_TITLE
from models.cache import Cache
from models.preset import Preset
from models.settings import Settings
from modules.generator import preset_generator
from modules.swf_parser import swf_parser
from src.modules.find_preview_image import find_preview_image


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, preset: Preset, cache: Cache):
        super().__init__()
        self.settings = settings
        self.preset = preset
        self.cache = cache
        # プリセット変更フラグ。
        # 何か設定を操作するようなアクションを起こしたらTrueにする。
        # プリセットを保存するアクションでFalseにする。
        self.preset_is_dirty = False

        self.setWindowTitle(PROGRAM_TITLE)
        self.resize(1100, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 上部 ---
        # フォントSWF読み込みフォルダ選択エリア
        self.setup_folder_selection(main_layout)
        # プリセット選択エリア
        self.setup_preset_selection(main_layout)

        # --- 中央 ---
        # ベースレイアウト
        content_layout = QHBoxLayout()
        # 左側: フォント名一覧
        self.setup_left_panel(content_layout)
        # 右側：カテゴリ別マッピング
        self.setup_right_panel(content_layout)
        main_layout.addLayout(content_layout)

        # --- 下部：実行エリア ---
        bottom_area = QVBoxLayout()  # 垂直レイアウトで入力欄とボタンを分ける

        # --- validNameChars 入力セクション ---
        valid_chars_layout = QHBoxLayout()
        valid_chars_label = QLabel("ValidNameChars:")
        self.valid_chars_edit = QLineEdit()  # 1行入力欄
        self.valid_chars_edit.setText(self.preset.valid_name_chars)
        self.valid_chars_edit.setPlaceholderText("$-_0123456789...")
        self.valid_chars_edit.textChanged.connect(self.on_valid_chars_changed)

        valid_chars_layout.addWidget(valid_chars_label)
        valid_chars_layout.addWidget(self.valid_chars_edit, stretch=1)
        # validNameCharsのレイアウトを bottom_area に入れる
        bottom_area.addLayout(valid_chars_layout)

        # --- ボタンエリア ---
        save_layout = QHBoxLayout()

        btn_save_config = QPushButton("現在のユーザープリセット設定を保存")
        btn_save_config.setFixedHeight(45)
        btn_save_config.clicked.connect(self.save_current_preset)

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
        main_layout.addLayout(bottom_area)

        # 画面起動時の初期動作
        # 初期値を読み込んだり起動環境を確認したり
        self.window_init()

    def window_init(self):
        # プリセットにSWFフォルダが設定されていて、ちゃんと存在していれば表示する。
        if self.preset.swf_dir and self.preset.swf_dir.exists():
            # resolveしなくても、もともと絶対パスで入ってる。
            self.swf_dir_path_label.setText(
                f"参照中のSWFフォルダ: {self.preset.swf_dir}"
            )
        else:
            self.swf_dir_path_label.setText("参照中のSWFフォルダ: (未設定)")

    def setup_folder_selection(self, layout):
        folder_layout = QHBoxLayout()

        # パスの表示ラベル
        path = str(self.preset.swf_dir) if self.preset.swf_dir else "未選択"
        self.swf_dir_path_label = QLabel(f"現在のフォルダ: {path}")

        # フォルダ選択ボタン
        btn_browse = QPushButton("フォルダを開く")
        btn_browse.clicked.connect(self.select_folder)

        # 読み込みボタン
        # 強制スキャンはさせたくないが、一覧が更新されないため、利用者の動線を活用する
        # 再スキャンという名前をやめて、フォントを読み込むという名前にすれば、一覧が空なら押してくれるはず。
        self.btn_rescan = QPushButton("フォントを読み込む")
        self.btn_rescan.clicked.connect(self.on_rescan_clicked)
        self.btn_rescan.setEnabled(bool(self.preset.swf_dir))

        # レイアウトへの追加順序（左からラベル、開く、フォントを読み込む）
        folder_layout.addWidget(self.swf_dir_path_label, stretch=1)
        folder_layout.addWidget(btn_browse)  # ←これが抜けていました！
        folder_layout.addWidget(self.btn_rescan)

        layout.addLayout(folder_layout)

    def setup_preset_selection(self, layout):
        """プリセットの切り替えと別名保存のUIを構築"""

        preset_group = QGroupBox("プリセット管理")
        preset_layout = QHBoxLayout(preset_group)

        # 1. プリセット選択
        preset_layout.addWidget(QLabel("プリセット:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        self.refresh_preset_list()  # ファイル一覧を取得
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo, stretch=1)

        # 2. 別名保存ボタン
        btn_save_as = QPushButton("別名で保存...")
        btn_save_as.clicked.connect(self.on_preset_save_as_clicked)
        preset_layout.addWidget(btn_save_as)

        layout.addWidget(preset_group)

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
        self.valid_chars_edit.setText(self.preset.valid_name_chars)

        # 各フォントマッピングのコンボボックスを更新
        for map_name, combo in self.combos.items():
            font_name = self.preset.get_mapping_font(map_name)
            combo.blockSignals(True)
            # もし現在のリストにないフォント名なら追加して選択
            if font_name and combo.findText(font_name) == -1:
                combo.addItem(font_name, font_name)
            combo.setCurrentText(font_name if font_name else "-- 選択なし --")
            combo.blockSignals(False)

        # 未保存フラグをリセット
        self.preset_is_dirty = False
        self.setWindowTitle(PROGRAM_TITLE)

    def setup_left_panel(self, layout):
        left_group = QGroupBox("検出されたフォント名")
        left_layout = QVBoxLayout(left_group)

        # フォントリスト
        self.font_list_widget = QListWidget()
        # 項目が選択されたらプレビューを更新するシグナルを接続
        self.font_list_widget.itemSelectionChanged.connect(self.update_font_preview)
        left_layout.addWidget(self.font_list_widget, stretch=2)

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

    def setup_right_panel(self, layout):
        right_group = QGroupBox("fontconfig マッピング (カテゴリ別)")
        right_main_layout = QVBoxLayout(right_group)

        self.tabs = QTabWidget()
        self.combos = {}

        for group in BASE_GROUP:
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
                    "プリセットファイル(presets\プリセット名.yml)の mappings に、base_group: custom で追加登録することで表示されます。"
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
                lambda _, g=group: self.apply_font_to_group(g)
            )
            tab_v_layout.addWidget(btn_apply_all)

            # --- 各マッピング行 ---
            form_widget = QWidget()
            tab_layout = QFormLayout(form_widget)

            group_mappings = [
                m for m in self.preset.mappings if m["base_group"] == group
            ]
            for m in group_mappings:
                map_name = m["map_name"]

                # 行全体を管理するレイアウト
                row_layout = QHBoxLayout()

                # 1. 適用ボタン 「>>」 (左端)
                btn_apply = QPushButton(">>")
                btn_apply.setFixedWidth(35)  # さらにコンパクトに
                btn_apply.setToolTip("選択中のフォントをここに適用")
                btn_apply.clicked.connect(
                    lambda _, n=map_name: self.apply_selected_to_row(n)
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
    def apply_selected_to_row(self, map_name: str):
        """左のリストで選択されているフォント名を、指定した行のコンボボックスにセットする"""
        selected_item = self.font_list_widget.currentItem()
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

    def apply_font_to_group(self, group_name: str):
        """左のリストで選択されているフォント名を、グループ内の全ての行に適用する"""
        selected_item = self.font_list_widget.currentItem()
        if not selected_item:
            return

        font_name = selected_item.text()
        group_mappings = [
            m for m in self.preset.mappings if m["base_group"] == group_name
        ]

        for m in group_mappings:
            self.apply_selected_to_row(m["map_name"])

    def refresh_ui_from_cache(self):
        """スキャンを行わず、現在のフォルダ配下のキャッシュデータのみをUIに反映する"""
        if not self.preset.swf_dir:
            self.font_list_widget.clear()
            return

        # 比較用に Path オブジェクト化
        current_swf_dir = Path(self.preset.swf_dir).resolve()

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
        self.font_list_widget.clear()
        self.font_list_widget.addItems(sorted_fonts)
        self.update_combos_with_detected(sorted_fonts)

    # --- 新設：再スキャンボタンのアクション ---
    def on_rescan_clicked(self):
        """明示的にスキャンを実行する"""
        if self.preset.swf_dir and self.preset.swf_dir.exists():
            self.refresh_fonts(self.preset.swf_dir)
            # QMessageBox.information(self, "完了", "フォントの読み込みが完了しました。")
        else:
            QMessageBox.warning(self, "エラー", "フォルダが見つかりません。")

    # select_folder の最後でボタンの有効化状態を更新するように修正
    def select_folder(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "フォントSWFが含まれるフォルダを選択"
        )
        if dir_path:
            p = Path(dir_path)
            self.preset.swf_dir = p
            self.swf_dir_path_label.setText(f"現在のフォルダ: {str(p)}")
            self.btn_rescan.setEnabled(True)  # ボタンを有効化
            self.refresh_fonts(p)
            self.preset.save()

    def refresh_fonts(self, swf_dir_path: Path):
        if not self.check_environment():
            return

        message = (
            "フォントリストを更新しています...\n"
            "※フォントファイル数が多い場合、解析に時間がかかることがあります。"
        )
        progress = QProgressDialog(message, None, 0, 0, self)
        progress.setWindowTitle("処理中")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        QGuiApplication.processEvents()

        try:
            # 1. フォルダが変わったので、今回のスキャン結果を入れる変数は空から始める
            detected = set()

            # スキャン実行
            for swf_path in swf_dir_path.rglob("*.swf"):
                # swf_parser内でキャッシュの有無を確認しているはずですが、
                # ここで再度解析を依頼
                font_names = swf_parser(
                    swf_path=swf_path,
                    cache=self.cache.data,  # 最新のキャッシュデータを渡す
                    debug=False,
                )

                if font_names:
                    # 全体キャッシュ(self.cache.data)は壊さず、新しい情報を追加・更新する
                    self.cache.update_swf_cache(
                        swf_path=swf_path, font_names=font_names, swf_dir=swf_dir_path
                    )
                    # ★「今回の表示対象」にだけ追加
                    detected.update(font_names)

            # キャッシュ全体を保存（他のフォルダのデータも維持されたまま保存されます）
            self.cache.save()

            # UI反映
            sorted_fonts = sorted(list(detected))
            self.font_list_widget.clear()
            self.font_list_widget.addItems(sorted_fonts)
            self.update_combos_with_detected(sorted_fonts)

        except Exception as e:
            print(f"スキャンエラー: {e}")
            QMessageBox.critical(
                self, "エラー", f"スキャン中にエラーが発生しました:\n{e}"
            )
        finally:
            progress.close()

    def update_font_preview(self):
        """リストで選択されたフォントのプレビュー画像を表示する"""
        selected_item = self.font_list_widget.currentItem()
        if not selected_item:
            self.preview_label.setText("No selection")
            self.preview_label.setPixmap(QPixmap())  # クリア
            return

        font_name = selected_item.text()

        # 1. キャッシュからこのフォント名を持つ SWF パスを探す
        found_swf_path = None
        for entry in self.cache.data:
            if font_name in entry.get("font_names", []):
                # 保存されている相対パスを絶対パスに戻す
                found_swf_path = self.preset.swf_dir / entry["swf_path"]
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
            current_val = self.preset.get_mapping_font(map_name)

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
            self.settings.last_preset_name = str(new_preset_name_norm)
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
                self.save_current_preset()
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
            self.settings.last_preset_name = str(new_path)
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
                    self.setWindowTitle(f"{PROGRAM_TITLE} *")
                break
        # self.config.save() はここでは呼ばない！

    def on_valid_chars_changed(self, text):
        """文字セットが変更されたらフラグを立てる"""
        if self.preset.valid_name_chars != text:
            self.preset.valid_name_chars = text
            self.preset_is_dirty = True
            self.setWindowTitle(f"{PROGRAM_TITLE} *")

    def on_generate_clicked(self):
        try:
            # --- 0. バリデーション：必須項目チェック ---
            missing_fields = []
            for m in self.preset.mappings:
                # flag に 'require' が設定されている、かつフォント名が空（または "-- 選択なし --"）
                if m.get("flag") == "require" and (
                    not m.get("font_name") or m.get("font_name") == ""
                ):
                    # 分かりやすいようにマップ名（または表示名）をリストに追加
                    missing_fields.append(f"・{m['map_name']}")

            if missing_fields:
                error_msg = "以下の必須項目が設定されていません。フォントを選択してください：\n\n" + "\n".join(
                    missing_fields
                )
                QMessageBox.warning(self, "入力チェック", error_msg)

                # 該当する項目があるタブに自動で切り替える、なんていう「おせっかい機能」も可能ですが
                # まずは警告を出して止めるのが一番安全です。
                return

            # --- 0.5 バリデーション：フォントの存在チェック ---
            # 現在のリスト(UI)に表示されているフォントをセットにする
            available_fonts = {
                self.font_list_widget.item(i).text()
                for i in range(self.font_list_widget.count())
            }

            not_found_in_list = []
            for m in self.preset.mappings:
                f_name = m.get("font_name")
                # 設定されているのに、今のフォルダのスキャン結果に含まれていない場合
                if f_name and f_name not in available_fonts:
                    not_found_in_list.append(f"・{m['map_name']}: {f_name}")

            if not_found_in_list:
                # コンソールに警告を出す
                print(
                    "\n⚠️ [WARNING] 設定されたフォントが現在のフォルダ内に見つかりません:"
                )
                for item in not_found_in_list:
                    print(f"  {item}")

                warning_msg = (
                    "以下の設定済みフォントマップにて、紐づくフォントSWFが存在しません。\n"
                    "そのまま出力しますか？（UI全体が豆腐化する可能性があります）\n\n"
                    + "\n".join(not_found_in_list)
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

            # --- 1. 出力先フォルダの決定 ---
            # 前回の設定があればそれを、なければ現在のディレクトリ（"."）を初期値にする
            initial_dir = str(self.preset.output_dir) if self.preset.output_dir else "."

            selected_dir = QFileDialog.getExistingDirectory(
                self,
                "ユーザープリセットの出力先フォルダを選択してください",
                initial_dir,
            )

            # キャンセルされたら処理を中断
            if not selected_dir:
                print("出力がキャンセルされました。")
                return

            # 新しいパスを保存（次回のために更新）
            self.preset.output_dir = Path(selected_dir)
            self.preset.save()

            # --- 2. 生成処理実行 ---
            out_file = preset_generator(self.preset, self.cache.data)

            # --- 3. 完了通知 ---
            print(f"✅ 生成成功: {out_file}")

            # せっかくなので、保存先をすぐ確認できるように「フォルダを開く」ボタン付きのボックスにしましょう
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("完了")
            msg_box.setText(f"生成が完了しました！\n\n出力先:\n{out_file.parent}")
            msg_box.setIcon(QMessageBox.Information)
            open_folder_btn = msg_box.addButton("出力先を開く", QMessageBox.ActionRole)
            msg_box.addButton("閉じる", QMessageBox.AcceptRole)

            msg_box.exec()

            # 「出力先を開く」が押されたらエクスプローラーで開く
            if msg_box.clickedButton() == open_folder_btn:
                os.startfile(out_file.parent)

        except Exception as e:
            print(f"❌ 生成失敗: {e}")
            QMessageBox.critical(self, "エラー", f"生成中にエラーが発生しました:\n{e}")

    def save_current_preset(self):
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
            self.preset.save()
            self.preset_is_dirty = False
            # タイトルの * を消す
            self.setWindowTitle(PROGRAM_TITLE)
            print("✅ ユーザープリセットを保存しました。")
            # 下部にステータスバーがあればそこに出してもいいですが、とりあえず標準出力
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
                self.save_current_preset()
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

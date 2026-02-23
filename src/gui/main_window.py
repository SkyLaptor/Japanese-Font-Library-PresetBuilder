import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
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


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, user_config: Preset, cache: Cache):
        super().__init__()
        self.settings = settings
        self.user_config = user_config
        self.user_config_is_dirty = False  # ユーザー設定変更フラグ
        self.cache = cache
        self.setWindowTitle(PROGRAM_TITLE)
        self.resize(1100, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 上部：フォルダ選択 ---
        self.setup_folder_selection(main_layout)

        # --- ★ここに追加：プリセット選択エリア ---
        self.setup_preset_selection(main_layout)

        # --- 中央：コンテンツエリア ---
        content_layout = QHBoxLayout()

        # 左側：検出されたフォント一覧
        self.setup_left_panel(content_layout)

        # 右側：タブによるカテゴリ別マッピング
        self.setup_right_panel(content_layout)

        main_layout.addLayout(content_layout)

        # --- 下部：実行エリア ---
        bottom_area = QVBoxLayout()  # 垂直レイアウトで入力欄とボタンを分ける

        # --- validNameChars 入力セクション ---
        valid_chars_layout = QHBoxLayout()
        valid_chars_label = QLabel("ValidNameChars:")
        self.valid_chars_edit = QLineEdit()  # 1行入力欄
        self.valid_chars_edit.setText(self.user_config.valid_name_chars)
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
        btn_save_config.clicked.connect(self.save_current_config)

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

        # 起動時の初期スキャン
        self.initial_scan()

    def initial_scan(self):
        """起動時の初期動作を管理"""
        # 1. まずはFFDecのチェック（ダメならここで即終了）
        ffdec_check = self.check_environment()
        if not ffdec_check:
            sys.exit(1)

        # 2. SWFパスがあるかチェック
        if self.user_config.swf_dir and self.user_config.swf_dir.exists():
            # パスがあるならスキャン
            self.refresh_fonts(self.user_config.swf_dir)
        else:
            # パスが空、またはフォルダが存在しない場合
            print("SWFフォルダが未設定です。選択して下さい。")
            self.path_label.setText("SWFフォルダが未設定です。選択して下さい。")

    def check_environment(self):
        """環境チェック：FFDecが存在するか"""
        if not Path(self.settings.ffdec_cli).exists():
            QMessageBox.critical(
                self,
                "環境エラー",
                f"FFDecが見つかりません。\nパスを確認してください:\n{self.settings.ffdec_cli}",
            )
            return False
        return True

    def setup_folder_selection(self, layout):
        folder_layout = QHBoxLayout()
        path = str(self.user_config.swf_dir) if self.user_config.swf_dir else "未選択"
        self.path_label = QLabel(f"現在のフォルダ: {path}")
        btn_browse = QPushButton("フォルダを開く")
        btn_browse.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.path_label, stretch=1)
        folder_layout.addWidget(btn_browse)
        layout.addLayout(folder_layout)

    def setup_preset_selection(self, layout):
        """プリセットの切り替えと別名保存のUIを構築"""

        preset_group = QGroupBox("ユーザープリセット管理")
        preset_layout = QHBoxLayout(preset_group)

        # 1. プリセット選択
        preset_layout.addWidget(QLabel("プロファイル:"))
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

        # ここを修正: config_path -> user_config_path
        current_name = self.user_config.preset_path.stem

        presets = sorted(list(PRESETS_DIR.glob("*.yml")))
        for p in presets:
            self.preset_combo.addItem(p.stem)

        self.preset_combo.setCurrentText(current_name)
        self.preset_combo.blockSignals(False)

    def refresh_ui_from_config(self):
        """現在の self.user_config の内容を UI（各コンボボックス等）に再反映させる"""
        # ValidNameCharsを更新
        self.valid_chars_edit.setText(self.user_config.valid_name_chars)

        # 各フォントマッピングのコンボボックスを更新
        for map_name, combo in self.combos.items():
            font_name = self.user_config.get_mapping_font(map_name)
            combo.blockSignals(True)
            # もし現在のリストにないフォント名なら追加して選択
            if font_name and combo.findText(font_name) == -1:
                combo.addItem(font_name, font_name)
            combo.setCurrentText(font_name if font_name else "-- 選択なし --")
            combo.blockSignals(False)

        # 未保存フラグをリセット
        self.user_config_is_dirty = False
        self.setWindowTitle(PROGRAM_TITLE)

    def setup_left_panel(self, layout):
        left_group = QGroupBox("検出されたフォント名")
        left_layout = QVBoxLayout(left_group)
        self.font_list_widget = QListWidget()
        left_layout.addWidget(self.font_list_widget)
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
                tab_v_layout.addWidget(info_label)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "console":
                info_label = QLabel("コンソールウィンドウで使用されるフォントです。")
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                tab_v_layout.addWidget(info_label)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "every":
                info_label = QLabel("UI全般で使用されるフォントです。")
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                tab_v_layout.addWidget(info_label)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "book":
                info_label = QLabel("本で使用されるフォントです。")
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                tab_v_layout.addWidget(info_label)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "handwrite":
                info_label = QLabel("手紙、メモで使用されるフォントです。")
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                tab_v_layout.addWidget(info_label)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "mcm":
                info_label = QLabel(
                    "JapaneseFontLibraryのMCMフォントマップパッチ適用状態で使用されるフォントです。"
                )
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                tab_v_layout.addWidget(info_label)
                info_label.setMaximumHeight(80)
                tab_v_layout.addWidget(info_label)
            if group == "custom":
                info_label = QLabel(
                    "独自に追加されたマップです。<br>"
                    "ユーザー設定ファイル(user_config.yml)の mappings に、base_group: custom で登録することで表示されます。"
                )
                info_label.setStyleSheet(normal_infolabel_style)
                info_label.setWordWrap(True)
                tab_v_layout.addWidget(info_label)
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
                m for m in self.user_config.mappings if m["base_group"] == group
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
            m for m in self.user_config.mappings if m["base_group"] == group_name
        ]

        for m in group_mappings:
            self.apply_selected_to_row(m["map_name"])

    def select_folder(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "フォントSWFが含まれるフォルダを選択"
        )
        if dir_path:
            p = Path(dir_path)
            self.user_config.swf_dir = p
            self.path_label.setText(f"現在のフォルダ: {str(p)}")
            self.refresh_fonts(p)
            self.user_config.save()

    def refresh_fonts(self, swf_dir_path: Path):
        # 1. 環境チェック
        if not self.check_environment():
            return

        # 2. 「更新中」ダイアログの表示
        # 進行状況が数値で測りづらいので、ぐるぐる回るモード(Range 0,0)にします
        message = (
            "フォントリストを更新しています...\n"
            "※フォントファイル数が多い場合、解析に時間がかかることがあります。"
        )
        progress = QProgressDialog(message, None, 0, 0, self)
        progress.setWindowTitle("処理中")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)  # キャンセル不可
        progress.show()

        # 処理がUIに反映されるように一瞬イベントを回す
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.processEvents()

        try:
            self.font_list_widget.clear()
            detected = []
            current_cache = self.cache.data
            cache_updated = False

            # スキャン実行
            for swf_path in swf_dir_path.rglob("*.swf"):
                # swf_parser実行
                font_names = swf_parser(
                    swf_path=swf_path,
                    settings=self.settings,
                    cache=current_cache,
                    debug=False,
                )
                # 都度キャッシュ保存（途中で落ちても良いように）
                self.cache.update_swf_cache(
                    swf_path=swf_path, font_names=font_names, swf_dir=swf_dir_path
                )
                self.cache.save()
                cache_updated = True
                for f in font_names:
                    if f not in detected:
                        detected.append(f)

            # TODO: これいる？
            # if cache_updated:
            #     self.user_config.save()

            detected.sort()
            self.font_list_widget.addItems(detected)

            # コンボボックスの更新処理... (中略)
            self.update_combos_with_detected(detected)  # 分離しておくと楽

        finally:
            # 3. 終わったら必ずダイアログを閉じる
            progress.close()

    def update_combos_with_detected(self, detected):
        """コンボボックスの中身を更新する"""
        for map_name, combo in self.combos.items():
            # 現在 YAML に保存されている値を取得
            current_val = self.user_config.get_mapping_font(map_name)

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
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            "プリセットの別名保存",
            "プリセット名を入力してください:",
            QLineEdit.Normal,
        )

        if ok and name:
            # 拡張子補完
            file_name = name if name.endswith(".yml") else f"{name}.yml"
            new_path = PRESETS_DIR / file_name

            # 保存して切り替え
            self.user_config.preset_path = new_path
            self.user_config.save()

            # Settingsも更新
            self.settings.last_preset_path = str(new_path)
            self.settings.save()

            # UIのリストを更新して、今作ったものを選択状態にする
            self.refresh_preset_list()
            QMessageBox.information(
                self, "完了", f"プリセット '{name}' を作成しました。"
            )

    def on_preset_changed(self, preset_name):
        from const import PRESETS_DIR

        if not preset_name:
            return

        preset_path = PRESETS_DIR / f"{preset_name}.yml"
        if preset_path.exists():
            # ここを修正: config_path -> user_config_path
            self.user_config.preset_path = preset_path
            self.user_config.load()

            # settingsへの保存（settings.settings だったことを忘れずに！）
            self.settings.settings["last_preset_path"] = str(preset_path)
            self.settings.save()

            self.refresh_ui_from_config()

    def on_mapping_changed(self, map_name, font_name):
        """設定値のメモリ上更新のみ行う"""
        # コンボボックスが空（リスト更新中など）の時は、メモリ上の設定を書き換えない
        if font_name == "" or font_name is None:
            return
        new_font = "" if font_name == "-- 選択なし --" else font_name
        for m in self.user_config.mappings:
            if m["map_name"] == map_name:
                # 値が本当に変わった時だけ Dirty フラグを立てる
                if m["font_name"] != new_font:
                    m["font_name"] = new_font
                    self.user_config_is_dirty = True
                    # タイトルに * をつけて「未保存」を視覚化
                    self.setWindowTitle(f"{PROGRAM_TITLE} *")
                break
        # self.config.save() はここでは呼ばない！

    def on_valid_chars_changed(self, text):
        """文字セットが変更されたらフラグを立てる"""
        if self.user_config.valid_name_chars != text:
            self.user_config.valid_name_chars = text
            self.user_config_is_dirty = True
            self.setWindowTitle(f"{PROGRAM_TITLE} *")

    def on_generate_clicked(self):
        try:
            # --- 0. バリデーション：必須項目チェック ---
            missing_fields = []
            for m in self.user_config.mappings:
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

            # --- 1. 出力先フォルダの決定 ---
            # 前回の設定があればそれを、なければ現在のディレクトリ（"."）を初期値にする
            initial_dir = (
                str(self.user_config.output_dir) if self.user_config.output_dir else "."
            )

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
            self.user_config.output_dir = Path(selected_dir)
            self.user_config.save()

            # --- 2. 生成処理実行 ---
            out_file = preset_generator(self.user_config, self.cache.data)

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
                import os

                os.startfile(out_file.parent)

        except Exception as e:
            print(f"❌ 生成失敗: {e}")
            QMessageBox.critical(self, "エラー", f"生成中にエラーが発生しました:\n{e}")

    def save_current_config(self):
        """現在のメモリ上の設定をファイルに書き出す"""
        # 必須項目が一つも埋まっていない、などの極端な状態なら警告
        filled_count = sum(1 for m in self.user_config.mappings if m.get("font_name"))
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
            self.user_config.save()
            self.user_config_is_dirty = False
            # タイトルの * を消す
            self.setWindowTitle(PROGRAM_TITLE)
            print("✅ ユーザープリセットを保存しました。")
            # 下部にステータスバーがあればそこに出してもいいですが、とりあえず標準出力
        except Exception as e:
            QMessageBox.critical(self, "保存エラー", f"設定の保存に失敗しました:\n{e}")

    def closeEvent(self, event):
        """閉じる時の保存確認"""
        from PySide6.QtWidgets import QMessageBox  # ここでインポートしてもOK

        if self.user_config_is_dirty:
            reply = QMessageBox.question(
                self,
                "保存の確認",
                "変更が保存されていません。保存してから閉じますか？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )

            if reply == QMessageBox.Yes:
                self.save_current_config()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()  # キャンセル
        else:
            event.accept()

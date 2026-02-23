import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from const import SETTINGS_FILE, USER_CONFIG_FILE
from models.settings import Settings
from models.user_config import UserConfig
from src.gui.main_window import MainWindow


def main():
    # アプリケーションの初期化
    app = QApplication(sys.argv)

    # システム設定ファイルの読み込み
    # 存在しなければハードコードされたデフォルト設定をロード
    settings_path = Path(SETTINGS_FILE)
    settings = Settings(settings_path)
    settings.load()

    # ユーザー設定ファイルの読み込み
    # 存在しなければハードコードされたデフォルト設定をロード
    user_config_path = Path(USER_CONFIG_FILE)
    user_config = UserConfig(user_config_path)
    user_config.load()

    # メインウィンドウの起動
    window = MainWindow(settings=settings, user_config=user_config)
    window.show()

    # 終了処理
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

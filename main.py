import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from const import CACHE_FILE, SETTINGS_FILE, USER_CONFIG_FILE
from models.cache import Cache
from models.preset import Preset
from models.settings import Settings
from src.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # 1. システム設定 (settings.yml)
    settings = Settings(Path(SETTINGS_FILE))
    settings.load()

    # 2. どのプリセットを使うか決定
    # 設定に記録があり、かつファイルが存在する場合のみそれを使う
    last_path = settings.last_preset_path
    if last_path and Path(last_path).exists():
        user_config_path = Path(last_path)
    else:
        user_config_path = Path(USER_CONFIG_FILE)

    # 3. ユーザー構成 (各プリセットyml)
    user_config = Preset(user_config_path)
    user_config.load()

    # 4. キャッシュ
    cache = Cache(Path(CACHE_FILE))
    cache.load()

    window = MainWindow(settings=settings, user_config=user_config, cache=cache)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

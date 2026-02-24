import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.const import CACHE_FILE, SETTINGS_FILE, USER_CONFIG_FILE
from src.gui.main_window import MainWindow
from src.models.cache import Cache
from src.models.preset import Preset
from src.models.settings import Settings


def main():
    app = QApplication(sys.argv)

    # 1. システム設定を読み込み
    settings = Settings(Path(SETTINGS_FILE))
    settings.load()

    # 2. どのプリセットを使うか決定
    # 最終プリセット設定がsettingsにあり、かつプリセットファイルが存在する場合にそれを使う
    last_preset_path = settings.last_preset_path
    if last_preset_path and Path(last_preset_path).exists():
        preset_path = Path(last_preset_path)
    else:
        preset_path = Path(USER_CONFIG_FILE)

    # 3. プリセットを読み込み
    preset = Preset(preset_path)
    preset.load()

    # 4. キャッシュを読み込み
    cache = Cache(Path(CACHE_FILE))
    cache.load()

    # GUI描画
    window = MainWindow(settings=settings, preset=preset, cache=cache)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

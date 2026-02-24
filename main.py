import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.const import CACHE_PATH, PRESETS_DIR, SETTINGS_FILE, USER_CONFIG_FILE
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
    last_preset_name = settings.last_preset_name
    # 最終プリセット設定がsettingsにあれば、PRESETS_DIR と合体させてフルパスを作る
    candidate_path = None
    if last_preset_name:
        candidate_path = PRESETS_DIR / last_preset_name
    # プリセットファイル（PRESETS_DIRの中の）が存在する場合にそれを使う
    if candidate_path is not None and candidate_path.exists():
        preset_path = candidate_path
    else:
        preset_path = Path(USER_CONFIG_FILE)

    # 3. プリセットを読み込み
    preset = Preset(preset_path)
    preset.load()

    # 4. キャッシュを読み込み
    cache = Cache(Path(CACHE_PATH))
    cache.load()

    # GUI描画
    window = MainWindow(settings=settings, preset=preset, cache=cache)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

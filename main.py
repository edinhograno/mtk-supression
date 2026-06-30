import sys
import queue
from config import Config
from audio_engine import AudioEngine
from first_run import run_if_needed
from settings_ui import SettingsUI
from tray import TrayApp


def main():
    config = Config()
    engine = AudioEngine()

    if not run_if_needed(config):
        sys.exit(0)

    device = config.get('input_device')
    if device:
        engine.set_input_device(device)
    engine.set_intensity(config.get('intensity', 0.75))

    if config.get('active', True):
        engine.start()

    cmd_queue = queue.Queue()
    ui = SettingsUI(config, engine)

    tray = TrayApp(
        config=config,
        engine=engine,
        on_settings=ui.request_show,
        on_quit=ui.request_quit,
    )
    tray.run_in_thread()

    # Blocks on main thread until quit command received
    ui.run_main_loop(cmd_queue)


if __name__ == '__main__':
    main()

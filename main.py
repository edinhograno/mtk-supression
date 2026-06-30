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

    was_first_run = config.get('first_run', True)
    if not run_if_needed(config):
        sys.exit(0)

    device_idx = config.get('input_device_index')
    if device_idx is not None:
        engine.set_input_device(device_idx)
    elif config.get('input_device'):
        engine.set_input_device(config.get('input_device'))
    engine.set_intensity(config.get('intensity', 0.75))

    if config.get('active', True):
        engine.start()

    cmd_queue = queue.Queue()
    ui = SettingsUI(config, engine, show_on_start=was_first_run)

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

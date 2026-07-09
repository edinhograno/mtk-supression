import threading
import pystray
from PIL import Image, ImageDraw

from config import Config
from audio_engine import AudioEngine


def _make_icon(active: bool) -> Image.Image:
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    c = (26, 122, 54, 255) if active else (192, 57, 43, 255)
    w = 4

    # Outer ear rim — open arc (C-shape, opening on the left)
    draw.arc([14, 8, 50, 52], start=210, end=330, fill=c, width=w)
    # Left side vertical connector (closes the C)
    draw.line([(15, 28), (15, 38)], fill=c, width=w)
    # Earlobe — small filled ellipse at bottom
    draw.ellipse([24, 48, 40, 60], fill=c)

    # Inner helix — smaller concentric arc
    draw.arc([22, 16, 42, 38], start=210, end=350, fill=c, width=3)

    # Ear canal — small filled dot
    draw.ellipse([28, 30, 36, 38], fill=c)

    if not active:
        # Diagonal slash overlay
        draw.line([(12, 12), (52, 52)], fill=(192, 57, 43, 178), width=w)

    return img


class TrayApp:
    def __init__(self, config: Config, engine: AudioEngine, on_settings, on_quit):
        self._config = config
        self._engine = engine
        self._on_settings = on_settings  # callable, called from tray thread
        self._on_quit = on_quit          # callable, called from tray thread
        self._icon = None

    def run_in_thread(self):
        """Start tray icon in a daemon thread. Returns immediately."""
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def update_icon(self):
        if self._icon:
            self._icon.icon = _make_icon(self._engine.is_running())

    def _run(self):
        self._icon = pystray.Icon(
            'MTKNoiseCanceller',
            _make_icon(self._engine.is_running()),
            'MTK Noise Canceller',
            menu=pystray.Menu(
                pystray.MenuItem('Configurações', self._open_settings),
                pystray.MenuItem('Ativar/Desativar', self._toggle),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('Sair', self._quit),
            ),
        )
        self._icon.run()

    def _toggle(self):
        if self._engine.is_running():
            self._engine.stop()
            self._config.set('active', False)
        else:
            self._engine.start()
            self._config.set('active', True)
        self._config.save()
        self.update_icon()

    def _open_settings(self):
        self._on_settings()

    def _quit(self):
        self._engine.stop()
        self._on_quit()
        if self._icon:
            self._icon.stop()

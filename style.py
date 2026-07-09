import winreg

COLOR_ACCENT   = '#0078D4'
COLOR_ACTIVE   = '#1a7a36'
COLOR_INACTIVE = '#c0392b'
COLOR_BG       = '#ffffff'
COLOR_CARD     = '#f8f9fa'
COLOR_BORDER   = '#eeeeee'
COLOR_TEXT     = '#222222'
COLOR_MUTED    = '#999999'

COLOR_BG_DARK     = '#1e1e1e'
COLOR_CARD_DARK   = '#2d2d2d'
COLOR_BORDER_DARK = '#3d3d3d'
COLOR_TEXT_DARK   = '#e0e0e0'
COLOR_MUTED_DARK  = '#888888'


def is_dark_mode() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
        ) as k:
            value, _ = winreg.QueryValueEx(k, 'AppsUseLightTheme')
            return value == 0
    except OSError:
        return False


def app_stylesheet(dark: bool = False) -> str:
    bg     = COLOR_BG_DARK     if dark else COLOR_BG
    card   = COLOR_CARD_DARK   if dark else COLOR_CARD
    border = COLOR_BORDER_DARK if dark else COLOR_BORDER
    text   = COLOR_TEXT_DARK   if dark else COLOR_TEXT
    groove = '#3d3d3d'         if dark else '#e0e0e0'
    hover  = '#3a3a3a'         if dark else '#eeeeee'
    press  = '#2a2a2a'         if dark else '#e0e0e0'
    cb_ind = '#2d2d2d'         if dark else 'white'

    return f"""
    QWidget {{
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 12px;
        color: {text};
        background-color: {bg};
    }}
    QComboBox {{
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px 10px;
        background: {card};
        color: {text};
    }}
    QComboBox:focus {{ border-color: {COLOR_ACCENT}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background: {card};
        color: {text};
        border: 1px solid {border};
        selection-background-color: {COLOR_ACCENT};
        selection-color: white;
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {groove};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {COLOR_ACCENT};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        width: 14px; height: 14px;
        background: {COLOR_ACCENT};
        border-radius: 7px;
        margin: -5px 0;
    }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border-radius: 4px;
        border: 2px solid {COLOR_ACCENT};
        background: {cb_ind};
    }}
    QCheckBox::indicator:checked {{
        background-color: {COLOR_ACCENT};
        border-color: {COLOR_ACCENT};
    }}
    QPushButton {{
        border: 1px solid {border};
        border-radius: 6px;
        padding: 5px 14px;
        background: {card};
        color: {text};
    }}
    QPushButton:hover {{ background: {hover}; }}
    QPushButton:pressed {{ background: {press}; }}
    """

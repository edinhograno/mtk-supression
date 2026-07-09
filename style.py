COLOR_ACCENT   = '#0078D4'
COLOR_ACTIVE   = '#1a7a36'
COLOR_INACTIVE = '#c0392b'
COLOR_BG       = '#ffffff'
COLOR_CARD     = '#f8f9fa'
COLOR_BORDER   = '#eeeeee'
COLOR_TEXT     = '#222222'
COLOR_MUTED    = '#999999'


def app_stylesheet() -> str:
    return f"""
    QWidget {{
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 12px;
        color: {COLOR_TEXT};
        background-color: {COLOR_BG};
    }}
    QComboBox {{
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        background: {COLOR_CARD};
    }}
    QComboBox:focus {{ border-color: {COLOR_ACCENT}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: #e0e0e0;
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
        background: white;
    }}
    QCheckBox::indicator:checked {{
        background-color: {COLOR_ACCENT};
        border-color: {COLOR_ACCENT};
    }}
    QPushButton {{
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 5px 14px;
        background: {COLOR_CARD};
        color: {COLOR_TEXT};
    }}
    QPushButton:hover {{ background: #eeeeee; }}
    QPushButton:pressed {{ background: #e0e0e0; }}
    """

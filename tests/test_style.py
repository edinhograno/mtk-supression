def test_color_constants_are_hex_strings():
    import style
    names = (
        'COLOR_ACCENT', 'COLOR_ACTIVE', 'COLOR_INACTIVE', 'COLOR_BG',
        'COLOR_CARD', 'COLOR_BORDER', 'COLOR_TEXT', 'COLOR_MUTED',
        'COLOR_BG_DARK', 'COLOR_CARD_DARK', 'COLOR_BORDER_DARK',
        'COLOR_TEXT_DARK', 'COLOR_MUTED_DARK',
    )
    for name in names:
        val = getattr(style, name)
        assert isinstance(val, str), f'{name} deve ser str'
        assert val.startswith('#'), f'{name} deve comecar com #'
        assert len(val) == 7, f'{name} deve ter 7 chars (#rrggbb)'


def test_color_values_match_spec():
    import style
    assert style.COLOR_ACCENT   == '#0078D4'
    assert style.COLOR_ACTIVE   == '#1a7a36'
    assert style.COLOR_INACTIVE == '#c0392b'
    assert style.COLOR_BG       == '#ffffff'
    assert style.COLOR_CARD     == '#f8f9fa'
    assert style.COLOR_BORDER   == '#eeeeee'
    assert style.COLOR_TEXT     == '#222222'
    assert style.COLOR_MUTED    == '#999999'
    assert style.COLOR_BG_DARK     == '#1e1e1e'
    assert style.COLOR_CARD_DARK   == '#2d2d2d'
    assert style.COLOR_BORDER_DARK == '#3d3d3d'
    assert style.COLOR_TEXT_DARK   == '#e0e0e0'
    assert style.COLOR_MUTED_DARK  == '#888888'


def test_app_stylesheet_light_returns_nonempty_string():
    import style
    sheet = style.app_stylesheet(dark=False)
    assert isinstance(sheet, str)
    assert len(sheet) > 100


def test_app_stylesheet_dark_returns_nonempty_string():
    import style
    sheet = style.app_stylesheet(dark=True)
    assert isinstance(sheet, str)
    assert len(sheet) > 100


def test_app_stylesheet_contains_required_selectors():
    import style
    for dark in (False, True):
        sheet = style.app_stylesheet(dark=dark)
        for selector in ('QWidget', 'QComboBox', 'QSlider', 'QCheckBox', 'QAbstractItemView'):
            assert selector in sheet, f'stylesheet dark={dark} deve conter {selector}'


def test_app_stylesheet_dark_uses_dark_bg():
    import style
    light = style.app_stylesheet(dark=False)
    dark = style.app_stylesheet(dark=True)
    assert style.COLOR_BG in light
    assert style.COLOR_BG_DARK in dark
    assert style.COLOR_BG_DARK not in light

def test_color_constants_are_hex_strings():
    import style
    names = (
        'COLOR_ACCENT', 'COLOR_ACTIVE', 'COLOR_INACTIVE', 'COLOR_BG',
        'COLOR_CARD', 'COLOR_BORDER', 'COLOR_TEXT', 'COLOR_MUTED',
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


def test_app_stylesheet_returns_nonempty_string():
    import style
    sheet = style.app_stylesheet()
    assert isinstance(sheet, str)
    assert len(sheet) > 100


def test_app_stylesheet_contains_required_selectors():
    import style
    sheet = style.app_stylesheet()
    for selector in ('QWidget', 'QComboBox', 'QSlider', 'QCheckBox'):
        assert selector in sheet, f'stylesheet deve conter {selector}'

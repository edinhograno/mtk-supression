def test_make_icon_returns_rgba_64x64_when_active():
    from tray import _make_icon
    img = _make_icon(True)
    assert img.size == (64, 64)
    assert img.mode == 'RGBA'


def test_make_icon_returns_rgba_64x64_when_inactive():
    from tray import _make_icon
    img = _make_icon(False)
    assert img.size == (64, 64)
    assert img.mode == 'RGBA'


def test_make_icon_active_has_green_pixels():
    from tray import _make_icon
    img = _make_icon(True)
    pixels = list(img.getdata())
    visible = [p for p in pixels if p[3] > 128]
    green = [p for p in visible if p[1] > p[0] and p[1] > p[2]]
    assert len(green) > 5, 'active icon deve ter pixels verdes visíveis'


def test_make_icon_inactive_has_red_pixels():
    from tray import _make_icon
    img = _make_icon(False)
    pixels = list(img.getdata())
    visible = [p for p in pixels if p[3] > 128]
    red = [p for p in visible if p[0] > p[1] and p[0] > p[2]]
    assert len(red) > 5, 'inactive icon deve ter pixels vermelhos visíveis'

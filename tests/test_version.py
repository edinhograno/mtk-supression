def test_version_format():
    from version import __version__
    parts = __version__.split('.')
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_version_is_string():
    from version import __version__
    assert isinstance(__version__, str)

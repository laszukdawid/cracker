from cracker.main import parse_args


def test_parse_args_enables_debug_and_preserves_qt_arguments():
    args, qt_args = parse_args(["--debug", "--platform", "offscreen"])

    assert args.debug is True
    assert qt_args == ["--platform", "offscreen"]


def test_parse_args_defaults_to_info_mode():
    args, qt_args = parse_args([])

    assert args.debug is False
    assert qt_args == []

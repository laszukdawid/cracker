import sys

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        arguments = ["cracker-test"]
        if sys.platform == "darwin":
            arguments.extend(["-platform", "offscreen"])
        app = QApplication(arguments)
    assert isinstance(app, QApplication)
    return app

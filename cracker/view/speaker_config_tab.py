import logging

from PyQt5.QtWidgets import QGridLayout, QLabel, QLineEdit, QWidget

from cracker.config import Configuration


class SpeakerConfig(QWidget):
    _logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()
        self.config = Configuration()

        user_config = self.config.read_config()
        self.aws_profile = user_config.get("polly", {}).get("profile_name", "default")
        self.aws_region = user_config.get("polly", {}).get("region_name", "")

        self._layout = QGridLayout()
        self.setLayout(self._layout)

        # Name section "AWS Polly"
        self.aws_polly_label = QLabel("AWS Polly")
        self._layout.addWidget(self.aws_polly_label, 0, 0, 1, 2)

        # AWS profile selector
        self.aws_profile_label = QLabel("AWS Profile")
        self.aws_profile_input = QLineEdit()
        self.aws_profile_input.setPlaceholderText("AWS Profile")
        self.aws_profile_input.setText(self.aws_profile)
        self._layout.addWidget(self.aws_profile_label, 1, 0)
        self._layout.addWidget(self.aws_profile_input, 1, 1)

        # AWS region selector
        self.aws_region_label = QLabel("AWS Region")
        self.aws_region_input = QLineEdit()
        self.aws_region_input.setPlaceholderText("AWS Region")
        self.aws_region_input.setText(self.aws_region)
        self._layout.addWidget(self.aws_region_label, 2, 0)
        self._layout.addWidget(self.aws_region_input, 2, 1)

    def confirm_action(self):
        self._logger.info("Confirming action")

        self.config.save_user_config(
            {
                "speakers": {
                    "polly": {
                        "profile_name": self.aws_profile_input.text(),
                        "region_name": self.aws_region_input.text(),
                    }
                }
            }
        )

        # self.config.aws_profile = self.aws_profile_input.text()
        # self.config.aws_region = self.aws_region_input.text()

    def clearLayout(layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

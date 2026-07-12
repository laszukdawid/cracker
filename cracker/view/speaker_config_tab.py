import logging

from PyQt5.QtWidgets import QComboBox, QGridLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QWidget

from cracker.aws_config import AWSSSOProfile, list_aws_profiles, load_sso_profile, save_sso_profile, start_sso_login
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
        self.aws_profile_input = QComboBox()
        self.aws_profile_input.setEditable(True)
        profiles = list_aws_profiles()
        self.aws_profile_input.addItems(profiles)
        if self.aws_profile not in profiles:
            self.aws_profile_input.addItem(self.aws_profile)
        self.aws_profile_input.setCurrentText(self.aws_profile)
        self._layout.addWidget(self.aws_profile_label, 1, 0)
        self._layout.addWidget(self.aws_profile_input, 1, 1)

        # AWS region selector
        self.aws_region_label = QLabel("AWS Region")
        self.aws_region_input = QLineEdit()
        self.aws_region_input.setPlaceholderText("AWS Region")
        self.aws_region_input.setText(self.aws_region)
        self._layout.addWidget(self.aws_region_label, 2, 0)
        self._layout.addWidget(self.aws_region_input, 2, 1)

        self.sso_label = QLabel("AWS IAM Identity Center (SSO)")
        self._layout.addWidget(self.sso_label, 3, 0, 1, 2)

        self.sso_session_input = self._add_input(4, "SSO Session", "company")
        self.sso_start_url_input = self._add_input(5, "Start URL", "https://company.awsapps.com/start")
        self.sso_region_input = self._add_input(6, "SSO Region", "us-east-1")
        self.sso_account_id_input = self._add_input(7, "AWS Account ID", "123456789012")
        self.sso_role_name_input = self._add_input(8, "Role Name", "DeveloperAccess")

        self.sso_login_btn = QPushButton("Save and sign in with SSO")
        self.sso_login_btn.released.connect(self.sign_in_with_sso)
        self._layout.addWidget(self.sso_login_btn, 9, 0, 1, 2)

        # Test connection button
        self.test_connection_btn = QPushButton("Test Connection")
        self.test_connection_btn.released.connect(self.test_connection)
        self._layout.addWidget(self.test_connection_btn, 10, 0, 1, 2)

        self.aws_profile_input.currentTextChanged.connect(self.load_selected_profile)
        self.load_selected_profile(self.aws_profile)

    def _add_input(self, row: int, label: str, placeholder: str) -> QLineEdit:
        input_widget = QLineEdit()
        input_widget.setPlaceholderText(placeholder)
        self._layout.addWidget(QLabel(label), row, 0)
        self._layout.addWidget(input_widget, row, 1)
        return input_widget

    def load_selected_profile(self, profile_name: str) -> None:
        profile = load_sso_profile(profile_name)
        inputs = (
            self.sso_session_input,
            self.sso_start_url_input,
            self.sso_region_input,
            self.sso_account_id_input,
            self.sso_role_name_input,
        )
        if profile is None:
            for input_widget in inputs:
                input_widget.clear()
            return

        self.sso_session_input.setText(profile.session_name)
        self.sso_start_url_input.setText(profile.start_url)
        self.sso_region_input.setText(profile.sso_region)
        self.sso_account_id_input.setText(profile.account_id)
        self.sso_role_name_input.setText(profile.role_name)
        if profile.region:
            self.aws_region_input.setText(profile.region)

    def _sso_profile(self) -> AWSSSOProfile:
        return AWSSSOProfile(
            profile_name=self.aws_profile_input.currentText().strip(),
            session_name=self.sso_session_input.text().strip(),
            start_url=self.sso_start_url_input.text().strip(),
            sso_region=self.sso_region_input.text().strip(),
            account_id=self.sso_account_id_input.text().strip(),
            role_name=self.sso_role_name_input.text().strip(),
            region=self.aws_region_input.text().strip(),
        )

    def _has_sso_settings(self) -> bool:
        return any(
            input_widget.text().strip()
            for input_widget in (
                self.sso_session_input,
                self.sso_start_url_input,
                self.sso_region_input,
                self.sso_account_id_input,
                self.sso_role_name_input,
            )
        )

    def sign_in_with_sso(self) -> None:
        try:
            profile = self._sso_profile()
            save_sso_profile(profile)
            self._save_cracker_profile()
            start_sso_login(profile.profile_name)
        except Exception as error:
            self._show_message(QMessageBox.Critical, "SSO sign-in failed", str(error))
            return
        self._show_message(
            QMessageBox.Information,
            "SSO sign-in started",
            f"Complete the AWS sign-in in your browser for profile '{profile.profile_name}'.",
        )

    def _show_message(self, icon, title: str, message: str) -> None:
        msg_box = QMessageBox(self)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def _save_cracker_profile(self) -> None:
        self.config.save_user_config(
            {
                "speakers": {
                    "polly": {
                        "profile_name": self.aws_profile_input.currentText().strip() or "default",
                        "region_name": self.aws_region_input.text().strip(),
                    }
                }
            }
        )

    def test_connection(self):
        """Test AWS Polly connection with the entered profile and region"""
        self._logger.info("Testing AWS Polly connection")

        profile_name = self.aws_profile_input.currentText().strip() or "default"
        region_name = self.aws_region_input.text() or None

        from cracker.speaker.polly import Polly

        try:
            # Test the connection
            success, message = Polly.test_connection(profile_name, region_name)

            # Show result dialog
            msg_box = QMessageBox()
            if success:
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle("Connection Successful")
                msg_box.setText("Successfully connected to AWS Polly!")
                msg_box.setInformativeText(message)
            else:
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("Connection Failed")
                msg_box.setText("Failed to connect to AWS Polly")
                msg_box.setInformativeText(message)

            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()

        except Exception as e:
            self._logger.error("Error testing connection: %s", e)
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Connection Test Error")
            msg_box.setText("An unexpected error occurred while testing the connection")
            msg_box.setInformativeText(str(e))
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()

    def confirm_action(self) -> bool:
        self._logger.info("Confirming action")

        try:
            if self._has_sso_settings():
                save_sso_profile(self._sso_profile())
            self._save_cracker_profile()
        except Exception as error:
            self._show_message(QMessageBox.Critical, "Unable to save AWS settings", str(error))
            return False
        return True

    def clearLayout(layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

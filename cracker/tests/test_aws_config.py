from pathlib import Path
from unittest.mock import patch

import pytest

from cracker.aws_config import (
    AWSConfigError,
    AWSSSOProfile,
    list_aws_profiles,
    load_sso_profile,
    save_sso_profile,
    start_sso_login,
)


def make_profile(**overrides) -> AWSSSOProfile:
    values = {
        "profile_name": "work",
        "session_name": "company",
        "start_url": "https://company.awsapps.com/start",
        "sso_region": "us-east-1",
        "account_id": "123456789012",
        "role_name": "DeveloperAccess",
        "region": "us-west-2",
    }
    values.update(overrides)
    return AWSSSOProfile(**values)


def test_save_and_load_sso_profile(tmp_path: Path):
    config_path = tmp_path / "config"

    save_sso_profile(make_profile(), config_path)

    assert list_aws_profiles(config_path) == ["work"]
    assert load_sso_profile("work", config_path) == make_profile()
    assert "sso_registration_scopes = sso:account:access" in config_path.read_text()


def test_save_sso_profile_preserves_unrelated_sections(tmp_path: Path):
    config_path = tmp_path / "config"
    config_path.write_text("[profile personal]\nregion = eu-west-1\n")

    save_sso_profile(make_profile(), config_path)

    assert "[profile personal]\nregion = eu-west-1" in config_path.read_text()
    assert list_aws_profiles(config_path) == ["personal", "work"]


def test_save_sso_profile_rejects_invalid_account_id(tmp_path: Path):
    with pytest.raises(AWSConfigError, match="12 digits"):
        save_sso_profile(make_profile(account_id="123"), tmp_path / "config")


@patch("cracker.aws_config.subprocess.Popen")
def test_start_sso_login_uses_selected_profile(popen):
    start_sso_login("work")

    popen.assert_called_once_with(
        ["aws", "sso", "login", "--profile", "work"],
        stdout=-3,
        stderr=-3,
    )

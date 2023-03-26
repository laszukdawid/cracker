from cracker.config import Configuration
from unittest.mock import MagicMock, patch


def test_read_config_defaul():
    config = Configuration()

    default_config = config.read_default_config()

    cracker_config = default_config["cracker"]
    assert cracker_config["speaker"] == "polly"
    assert cracker_config["speed"] == 4
    assert cracker_config["language"] == "english"


@patch("cracker.config.configuration.os.path.isdir", return_value=False)
def test_read_config(mock_isdir):
    config = Configuration()
    config.read_config()
    assert config.speaker == "polly"
    assert config.speed == 4
    assert config.language == "english"

    mock_isdir.assert_called_once_with(config.USER_CONFIG_DIR_PATH)


@patch("cracker.config.configuration.os.path.isfile", return_value=False)
@patch("cracker.config.configuration.os.path.isdir", return_value=True)
def test_read_user_config_dir_exists_file_not(mock_isdir, mock_isfile):
    config = Configuration()
    test_config = {"cracker": {"speaker": "polly", "speed": 2, "language": "pnglish"}}

    out = config._read_user_config(test_config)

    assert out == test_config

    mock_isdir.assert_called_once_with(config.USER_CONFIG_DIR_PATH)
    mock_isfile.assert_called_once_with(config.user_config_path)


@patch("cracker.config.configuration.os.path.isfile", return_value=True)
@patch("cracker.config.configuration.os.path.isdir", return_value=True)
def test_read_user_config_dir_file_exist(mock_isdir, mock_isfile):
    config = Configuration()
    test_config = {
        "cracker": {"speaker": "polly", "language": "polish", "voice": "maria"}
    }
    config._read_yaml = MagicMock(return_value=test_config)

    out = config._read_user_config(
        {
            "cracker": {
                "speaker": "polly",
                "language": "english",
                "speed": 2,
                "voice": "joanna",
            }
        }
    )

    assert out == {
        "cracker": {
            "speaker": "polly",
            "language": "polish",
            "speed": 2,
            "voice": "maria",
        }
    }

    mock_isdir.assert_called_once_with(config.USER_CONFIG_DIR_PATH)
    mock_isfile.assert_called_once_with(config.user_config_path)

def test_save_user_config():
    config = Configuration()
    config.speaker = "polly"
    config.speed = 2
    config.language = "english"
    config.voice = "joanna"
    config._default_config = {
        "cracker": {
            "speaker": "polly",
            "language": "english",
            "speed": 4,
            "voice": "joanna",
        }
    }
    config._write_yaml = MagicMock()

    config.save_user_config()

    config._write_yaml.assert_called_once_with(
        {
            "cracker": {
                "speaker": "polly",
                "language": "english",
                "speed": "2",
                "voice": "joanna",
            }
        },
        config.user_config_path,
    )

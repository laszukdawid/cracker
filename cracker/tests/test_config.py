from unittest.mock import MagicMock, patch

from cracker.config import Configuration


def test_read_config_defaul():
    config = Configuration()

    default_config = config.read_default_config()

    cracker_config = default_config["cracker"]
    assert cracker_config["speaker"] == "polly"
    assert cracker_config["speed"] == 4
    assert cracker_config["language"] == "English"


@patch("cracker.config.configuration.os.mkdir")
@patch("cracker.config.configuration.os.path.isfile", return_value=False)
@patch("cracker.config.configuration.os.path.isdir", return_value=False)
def test_read_config(mock_isdir, mock_isfile, mock_mkdir):
    config = Configuration()
    config.read_config()
    assert config.speaker == "polly"
    assert config.speed == 4
    assert config.language == "English"

    mock_mkdir.assert_called_once_with(config.USER_CONFIG_DIR_PATH)
    mock_isdir.assert_called_with(config.USER_CONFIG_DIR_PATH)
    mock_isfile.assert_called_once_with(config.user_parser_path)
    assert mock_isdir.call_count == 2


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
    test_config = {"cracker": {"speaker": "polly", "language": "Polish", "voice": "Maria"}}
    config._read_yaml = MagicMock(return_value=test_config)

    out = config._read_user_config(
        {
            "cracker": {
                "speaker": "polly",
                "language": "English",
                "speed": 2,
                "voice": "Joanna",
            }
        }
    )

    assert out == {
        "cracker": {
            "speaker": "polly",
            "language": "Polish",
            "speed": 2,
            "voice": "Maria",
        }
    }

    mock_isdir.assert_called_once_with(config.USER_CONFIG_DIR_PATH)
    mock_isfile.assert_called_once_with(config.user_config_path)


def test_save_user_config():
    config = Configuration()
    config.speaker = "polly"
    config.speed = 2
    config.language = "English"
    config.voice = "Joanna"
    config._default_config = {
        "cracker": {
            "speaker": "polly",
            "language": "English",
            "speed": 4,
            "voice": "Joanna",
        }
    }
    config._write_yaml = MagicMock()

    config.save_user_config()

    config._write_yaml.assert_called_once_with(
        {
            "cracker": {
                "speaker": "polly",
                "language": "English",
                "speed": "2",
                "voice": "Joanna",
            }
        }
    )

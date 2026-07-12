import configparser
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

_SECTION_HEADER = re.compile(r"^\s*\[[^]]+]\s*$")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class AWSSSOProfile:
    profile_name: str
    session_name: str
    start_url: str
    sso_region: str
    account_id: str
    role_name: str
    region: str


class AWSConfigError(ValueError):
    pass


def aws_config_path() -> Path:
    configured_path = os.environ.get("AWS_CONFIG_FILE", "~/.aws/config")
    return Path(configured_path).expanduser()


def list_aws_profiles(path: Path | None = None) -> list[str]:
    parser = _read_config(path or aws_config_path())
    profiles = []
    for section in parser.sections():
        if section == "default":
            profiles.append("default")
        elif section.startswith("profile "):
            profiles.append(section.removeprefix("profile "))
    return profiles


def load_sso_profile(profile_name: str, path: Path | None = None) -> AWSSSOProfile | None:
    parser = _read_config(path or aws_config_path())
    profile_section = _profile_section(profile_name)
    if not parser.has_section(profile_section):
        return None

    session_name = parser.get(profile_section, "sso_session", fallback="")
    session_section = f"sso-session {session_name}"
    if not session_name or not parser.has_section(session_section):
        return None

    return AWSSSOProfile(
        profile_name=profile_name,
        session_name=session_name,
        start_url=parser.get(session_section, "sso_start_url", fallback=""),
        sso_region=parser.get(session_section, "sso_region", fallback=""),
        account_id=parser.get(profile_section, "sso_account_id", fallback=""),
        role_name=parser.get(profile_section, "sso_role_name", fallback=""),
        region=parser.get(profile_section, "region", fallback=""),
    )


def save_sso_profile(profile: AWSSSOProfile, path: Path | None = None) -> None:
    _validate_profile(profile)
    config_path = path or aws_config_path()
    if config_path.is_symlink():
        config_path = config_path.resolve()
    text = config_path.read_text() if config_path.exists() else ""
    text = _upsert_section(
        text,
        _profile_section(profile.profile_name),
        {
            "sso_session": profile.session_name,
            "sso_account_id": profile.account_id,
            "sso_role_name": profile.role_name,
            "region": profile.region,
            "output": "json",
        },
    )
    text = _upsert_section(
        text,
        f"sso-session {profile.session_name}",
        {
            "sso_region": profile.sso_region,
            "sso_start_url": profile.start_url,
            "sso_registration_scopes": "sso:account:access",
        },
    )
    _atomic_write(config_path, text)


def start_sso_login(profile_name: str) -> subprocess.Popen:
    _validate_name("profile", profile_name)
    try:
        return subprocess.Popen(
            ["aws", "sso", "login", "--profile", profile_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as error:
        raise AWSConfigError("AWS CLI v2 is required to sign in with SSO") from error


def _read_config(path: Path) -> configparser.RawConfigParser:
    parser = configparser.RawConfigParser(interpolation=None)
    if path.exists():
        parser.read(path)
    return parser


def _profile_section(profile_name: str) -> str:
    return "default" if profile_name == "default" else f"profile {profile_name}"


def _validate_profile(profile: AWSSSOProfile) -> None:
    _validate_name("profile", profile.profile_name)
    _validate_name("SSO session", profile.session_name)
    required = {
        "SSO start URL": profile.start_url,
        "SSO region": profile.sso_region,
        "account ID": profile.account_id,
        "role name": profile.role_name,
        "AWS region": profile.region,
    }
    missing = [name for name, value in required.items() if not value.strip()]
    if missing:
        raise AWSConfigError(f"Missing required AWS SSO settings: {', '.join(missing)}")
    if not profile.account_id.isdigit() or len(profile.account_id) != 12:
        raise AWSConfigError("AWS account ID must contain exactly 12 digits")
    if any("\n" in value or "\r" in value for value in required.values()):
        raise AWSConfigError("AWS SSO settings must not contain line breaks")


def _validate_name(label: str, value: str) -> None:
    if not _SAFE_NAME.fullmatch(value):
        raise AWSConfigError(f"AWS {label} name may contain only letters, numbers, underscores, and hyphens")


def _upsert_section(text: str, section: str, values: dict[str, str]) -> str:
    lines = text.splitlines(keepends=True)
    header = f"[{section}]"
    start = next((index for index, line in enumerate(lines) if line.strip() == header), None)
    end = len(lines)
    if start is not None:
        end = next(
            (index for index in range(start + 1, len(lines)) if _SECTION_HEADER.match(lines[index])),
            len(lines),
        )

    block = [f"{header}\n", *(f"{key} = {value}\n" for key, value in values.items()), "\n"]
    if start is None:
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.extend(block)
    else:
        lines[start:end] = block
    return "".join(lines)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as temporary_file:
            temporary_file.write(text)
            temporary_path = Path(temporary_file.name)
        temporary_path.chmod(mode)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

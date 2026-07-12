from pathlib import Path
from zipfile import ZipFile

from cracker import __version__

REQUIRED_FILES = {
    "cracker/config/default.yaml",
    "cracker/config/parser.json",
    "cracker/icon.jpeg",
    "cracker/icon.png",
}
FORBIDDEN_PREFIXES = ("cracker/tests/",)


def main() -> None:
    wheels = list(Path("dist").glob(f"cracker-{__version__}-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected exactly one Cracker {__version__} wheel in dist/, found {len(wheels)}")

    with ZipFile(wheels[0]) as archive:
        packaged_files = set(archive.namelist())

    missing_files = sorted(REQUIRED_FILES - packaged_files)
    forbidden_files = sorted(filename for filename in packaged_files if filename.startswith(FORBIDDEN_PREFIXES))
    if missing_files or forbidden_files:
        problems = []
        if missing_files:
            problems.append(f"missing required files: {', '.join(missing_files)}")
        if forbidden_files:
            problems.append(f"contains test files: {', '.join(forbidden_files)}")
        raise SystemExit("Invalid wheel: " + "; ".join(problems))

    print(f"Validated wheel contents: {wheels[0]}")


if __name__ == "__main__":
    main()

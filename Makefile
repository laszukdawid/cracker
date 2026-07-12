UV = uv
RUN = ${UV} run
SOURCE_PATHS = cracker scripts

build:
	${UV} build
	${RUN} python scripts/check_wheel.py

clean:
	find cracker -name "*.pyc" -exec rm {} +
	find cracker -name "__pycache__" -prune -exec rm -r {} +
	rm -r cracker.egg-info 2> /dev/null || true
	rm -r build dist  2> /dev/null || true

format-code:
	${RUN} --extra dev ruff check --fix ${SOURCE_PATHS}
	${RUN} --extra dev ruff format ${SOURCE_PATHS}

format-check:
	${RUN} --extra dev ruff check ${SOURCE_PATHS}
	${RUN} --extra dev ruff format --check ${SOURCE_PATHS}

typecheck:
	${RUN} --extra dev ty check

install:
	${UV} sync

install-all:
	${UV} sync --all-extras

run:
	${RUN} cracker

upgrade:
	${UV} lock --upgrade

publish:
	${RUN} --extra build twine upload -r cracker dist/*

test:
	${RUN} --extra test pytest -v

check: format-check typecheck test build

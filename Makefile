UV = uv
RUN = ${UV} run

build:
	${UV} build

clean:
	find cracker -name "*.pyc" -exec rm {} +
	find cracker -name "__pycache__" -prune -exec rm -r {} +
	rm -r cracker.egg-info 2> /dev/null || true
	rm -r build dist  2> /dev/null || true

format-code:
	${RUN} --extra dev ruff check --fix cracker
	${RUN} --extra dev ruff format cracker

format-check:
	${RUN} --extra dev ruff check cracker
	${RUN} --extra dev ruff format --check cracker

typecheck:
	${RUN} --extra dev ty check

install:
	${UV} sync

install-all:
	${UV} sync --all-extras

upgrade:
	${UV} lock --upgrade

publish:
	${RUN} --extra build twine upload -r cracker dist/*

test:
	${RUN} --extra test pytest -v

check: format-check typecheck test build

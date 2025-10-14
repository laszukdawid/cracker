PYTHON = uv run python
PIP = uv pip

build:
	${PYTHON} -m build

clean:
	find cracker -name "*.pyc" -exec rm {} +
	find cracker -name "__pycache__" -prune -exec rm -r {} +
	rm -r cracker.egg-info 2> /dev/null || true
	rm -r build dist  2> /dev/null || true

format-code:
	${PYTHON} -m isort cracker
	${PYTHON} -m black cracker

upgrade:
	${PIP} install --upgrade pip setuptools

install: upgrade
	${PIP} install -e .

install-all: upgrade
	${PIP} install -e .[dev,build]

publish:
	${PYTHON} -m twine upload -r cracker dist/*

test:
	${PYTHON} -m pytest -v

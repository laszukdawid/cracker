build:
	python -m build

clean:
	find cracker -name "*.pyc" -exec rm {} +
	find cracker -name "__pycache__" -prune -exec rm -r {} +
	rm cracker.egg-info 2> /dev/null || true
	rm -r build dist  2> /dev/null || true

upgrade:
	pip install --upgrade pip setuptools

install: upgrade
	pip install -e .

install-all: upgrade
	pip install -e .[dev,build]

publish:
	python -m twine upload -r cracker dist/*

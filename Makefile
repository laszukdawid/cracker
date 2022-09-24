
clean:
	find . -name "*.pyc" -exec rm {} \;
	find . -name "__pycache__" -prune -exec rm -r {} \;
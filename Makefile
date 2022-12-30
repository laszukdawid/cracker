
clean:
	find . -name "*.pyc" -exec rm {} \;
	find . -name "__pycache__" -prune -exec rm -r {} \;
	find . -name "*.egg-info" -prune -exec rm -r {} \;
	rm -r build dist 

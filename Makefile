requirements.txt: poetry.lock
	poetry run pip freeze > $@

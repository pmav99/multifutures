.PHONY: list docs

list:
	@LC_ALL=C $(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'

init:
	poetry install --with dev --with docs --sync
	pre-commit install

style:
	pre-commit run black -a

lint:
	pre-commit run ruff -a

mypy:
	dmypy run multifutures

test:
	python -m pytest -vlx --durations=10 --durations-min=0.1

cov:
	coverage erase
	COVERAGE_PROCESS_START=.coveragerc pytest --cov --cov-report term-missing --durations=10 --durations-min=0.1

docs:
	mkdocs serve

deps:
	pre-commit run poetry-lock -a
	pre-commit run poetry-export -a

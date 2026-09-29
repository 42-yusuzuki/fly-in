.PHONY: install run debug clean lint lint-strict test build

install:
	uv sync

run:
	uv run fly-in $(ARGS)

debug:
	uv run python -m pdb -m flyin $(ARGS)

lint:
	uv run flake8 .
	uv run mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

test:
	uv run pytest

build:
	uv build

clean:
	rm -rf \
		.pytest_cache \
		.mypy_cache \
		build \
		dist
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +

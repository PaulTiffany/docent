.PHONY: install run test lint validate docker-build docker-run

install:
	python -m pip install -e '.[dev]'

run:
	uvicorn docent.app:app --host 0.0.0.0 --port 7860 --reload

test:
	pytest -q

lint:
	ruff check src tests

validate:
	python -m docent.cli validate

docker-build:
	docker build -t docent:local .

docker-run:
	docker run --rm -p 7860:7860 --env-file .env docent:local

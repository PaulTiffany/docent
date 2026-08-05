.PHONY: install run test lint validate audit build docker-build docker-run

install:
	python -m pip install -e '.[dev]'

run:
	uvicorn docent.app:app --host 0.0.0.0 --port 7860 --reload

test:
	pytest -q

lint:
	ruff format --check src tests tools deploy
	ruff check src tests tools deploy

audit:
	python -m docent.content_audit

validate:
	python -m docent.cli validate
	python -m docent.content_audit
	python -c "from docent.development import validate_main; validate_main()"
	python tools/frontend.py --check
	python tools/resources.py --check
	ruff format --check src tests tools deploy
	ruff check src tests tools deploy
	pytest -q

build:
	python -m build

docker-build:
	docker build -t docent:local .

docker-run:
	docker run --rm -p 7860:7860 --env-file .env docent:local

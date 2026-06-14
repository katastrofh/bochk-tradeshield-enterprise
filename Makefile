.PHONY: up down rebuild logs test local clean

up:
	docker compose up

down:
	docker compose down

rebuild:
	docker compose down
	docker compose build --no-cache app
	docker compose up

logs:
	docker compose logs -f app

test:
	pytest -q

local:
	uvicorn tradeshield.main:app --reload --host 0.0.0.0 --port 8000

clean:
	docker compose down -v --remove-orphans

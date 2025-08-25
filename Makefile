dev:
	docker-compose up --build

build:
	docker-compose build

up:
	docker-compose up -d

logs:
	docker-compose logs -f

migrate:
	docker-compose run --rm api alembic upgrade head

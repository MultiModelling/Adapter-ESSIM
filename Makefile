all: requirements
	docker-compose build

build-no-cache:
	docker-compose build --no-cache

dev:
	docker-compose up
dev-local:
	flask run -p 9203 --reload --debugger

infra:
	docker-compose -f docker-compose.infra.yml up
infra-daemon:
	docker-compose -f docker-compose.infra.yml up -d

db:
	docker-compose -f docker-compose.infra.yml up postgis pgadminer

down:
	docker-compose down
down-infra:
	docker-compose -f docker-compose.infra.yml down

dev-all: infra-daemon dev
down-all: down down-infra

compile-requirements:
	pip-compile
requirements:
	pip install -r requirements.txt

create-migration:
	flask db migrate
create-data-migration:
	flask db revision
apply-migrations:
	flask db upgrade
downgrade-migration:
	flask db downgrade

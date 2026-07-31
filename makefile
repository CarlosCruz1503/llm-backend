# Commands used for control and debug the project

build: 
	docker compose build 

rebuild-web: 
	docker compose up -d --build --renew-anon-volumes web

up: 
	docker compose up -d

stop:
	docker compose stop

bash:
	docker exec -it core_prompt bash

logs: 
	docker compose logs --tail 100 -f 

restart:
	make stop
	make up

migrations:
	docker exec -it core_prompt python manage.py makemigrations

migrate:
	docker exec -it core_prompt python manage.py migrate

superuser:
	docker exec -it core_prompt python manage.py createsuperuser
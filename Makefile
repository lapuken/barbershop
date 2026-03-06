ENV_FILE ?= .env

.PHONY: deploy update logs ps restart down backup restore admin migrate collectstatic shell

deploy:
	./deploy.sh

update:
	./scripts/update-app.sh --git-pull

logs:
	docker compose --env-file $(ENV_FILE) logs -f web db

ps:
	docker compose --env-file $(ENV_FILE) ps

restart:
	docker compose --env-file $(ENV_FILE) restart

down:
	docker compose --env-file $(ENV_FILE) down

backup:
	./backup.sh

restore:
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore FILE=backups/<timestamp>/database.dump"; exit 1; fi
	./scripts/restore-db.sh "$(FILE)"

admin:
	./scripts/create-initial-admin.sh

migrate:
	docker compose --env-file $(ENV_FILE) run --rm --no-deps -e RUN_COLLECTSTATIC=false web python manage.py migrate --noinput

collectstatic:
	docker compose --env-file $(ENV_FILE) run --rm --no-deps -e RUN_COLLECTSTATIC=false web python manage.py collectstatic --noinput

shell:
	docker compose --env-file $(ENV_FILE) exec web python manage.py shell

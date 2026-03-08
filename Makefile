ifneq ("$(wildcard ../env/.env)","")
ENV_FILE ?= ../env/.env
else
ENV_FILE ?= .env
endif

.PHONY: deploy update logs ps restart down backup restore restore-set rollback admin golive-init migrate collectstatic shell healthcheck diagnostics cleanup-backups prune-images

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

restore-set:
	@if [ -z "$(DIR)" ]; then echo "Usage: make restore-set DIR=../backups/<timestamp>"; exit 1; fi
	./restore.sh "$(DIR)"

rollback:
	./rollback.sh $(REF)

admin:
	./scripts/create-initial-admin.sh

golive-init:
	@if [ -z "$(FILE)" ]; then echo "Usage: make golive-init FILE=/opt/smartbarber/env/golive-init.json"; exit 1; fi
	./scripts/initialize-golive.sh "$(FILE)" $(ARGS)

migrate:
	docker compose --env-file $(ENV_FILE) run --rm --no-deps -e RUN_COLLECTSTATIC=false web python manage.py migrate --noinput

collectstatic:
	docker compose --env-file $(ENV_FILE) run --rm --no-deps -e RUN_COLLECTSTATIC=false web python manage.py collectstatic --noinput

shell:
	docker compose --env-file $(ENV_FILE) exec web python manage.py shell

healthcheck:
	./scripts/healthcheck.sh full

diagnostics:
	./scripts/diagnostics.sh

cleanup-backups:
	./scripts/cleanup-backups.sh

prune-images:
	./scripts/prune-docker.sh

# Set default goal to help, so if you run `make` it will display help
.DEFAULT_GOAL := help

# set app_web version from app_web/VERSION file as env variable
export APP_API_VERSION := $(shell cat app_api/VERSION)
export APP_WEB_VERSION := $(shell cat app_web/VERSION)
# this can be generated from `web` container: `make bash cont=web`
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
export CRYPT_SECRET_KEY_G_CLOUD_RUN = 'd5bPSqDR6o76p9osMLbm9cV0dVYjgCjWcyQL8-ArFFg='

status:
	@docker ps -a

up-net:
	@docker network create --driver bridge --subnet 162.100.0.0/16 doodleops_net

down-net:
	@docker network rm doodleops_net

build:
ifeq ($(cont),web)
	@docker compose -f ./deploy/local/docker-compose.yaml build app_web
else ifeq ($(cont),api)
	@docker compose -f ./deploy/local/docker-compose.yaml build app_api
else ifeq ($(cont),doc)
	@docker compose -f ./deploy/local/docker-compose.yaml build app_doc
else ifeq ($(cont),celery)
	@docker compose -f ./deploy/local/docker-compose.yaml build celery_worker
	@docker compose -f ./deploy/local/docker-compose.yaml build celery_beat
else ifneq ($(strip $(cont)),)
	@$(eval VERSION := $(lastword $(subst _, ,$(cont))))
	@$(eval SERVICE := $(patsubst %_$(VERSION),%, $(cont)))
	@echo "Service to be built: $(SERVICE)"
	@echo "Version to be built: $(VERSION)"
	@echo "Building $(cont) with tag:latest at $(PWD)/app_api/$(SERVICE)/cloud_run_container_$(SERVICE)/$(VERSION)"
	COMPOSE_DOCKER_CLI_BUILD=0 DOCKER_BUILDKIT=0 docker build --no-cache -t $(cont):latest $(PWD)/app_api/$(SERVICE)/cloud_run_container_$(SERVICE)/$(VERSION)
else
	@COMPOSE_DOCKER_CLI_BUILD=0 docker compose -f ./deploy/local/docker-compose.yaml -f ./deploy/local/docker-compose.api_apps.yaml build
endif


up:
	@if [ -z "$$(docker network ls -q -f name=doodleops_net)" ]; then \
		make up-net; \
	fi
ifeq ($(cont),web)
	@ENV_MODE=$(mode) docker compose -f ./deploy/local/docker-compose.yaml up app_web -d
else ifeq ($(cont),api)
	@ENV_MODE=$(mode) docker compose -f ./deploy/local/docker-compose.yaml up app_api -d
else ifeq ($(cont),api_apps)
	@ENV_MODE=$(mode) docker compose -f ./deploy/local/docker-compose.api_apps.yaml up -d
else ifeq ($(cont),db)
	@docker compose -f ./deploy/local/docker-compose.yaml up db -d
else ifeq ($(cont),redis_b)
	@docker compose -f ./deploy/local/docker-compose.yaml up redis-browser -d
else ifeq ($(cont),celery)
	@echo "After starting the Celery containers, please run the following commands:"
	@echo "make run cont=celery_worker"
	@echo "make run cont=celery_beat"
	@docker compose -f ./deploy/local/docker-compose.yaml up celery_worker -d
	@docker compose -f ./deploy/local/docker-compose.yaml up celery_beat -d
else ifneq ($(strip $(cont)),)
	@echo "Running all services... in `local` mode"
	@ENV_MODE=$(mode) docker compose -f ./deploy/local/docker-compose.yaml -f ./deploy/local/docker-compose.api_apps.yaml up -d $(cont)
else
	@echo "No container specified. Please provide a container name."
endif

up-api-apps:
# run sub-microservices for API apps in specific modes
ifeq ($(strip $(cont)),)
	$(error Example: make up-api-apps mode=local/dev/prod cont=app_docs_v1)
endif

ifeq ($(strip $(mode)),)
	$(error Error: mode is required)
endif

	@$(eval VERSION := $(lastword $(subst _, ,$(cont))))
	@$(eval SERVICE := $(patsubst %_$(VERSION),%, $(cont)))
	@echo "Service to be built: $(SERVICE)"
	@echo "Version to be built: $(VERSION)"
	@ENV_MODE=$(mode) docker compose -f ./deploy/local/docker-compose.api_apps.yaml up -d $(cont)

down:
ifeq ($(cont),web)
	@docker compose -f ./deploy/local/docker-compose.yaml down app_web
else ifeq ($(cont),api)
	@docker compose -f ./deploy/local/docker-compose.yaml down app_api
else ifeq ($(cont),db)
	@docker compose -f ./deploy/local/docker-compose.yaml down db
else ifeq ($(cont),celery)
	@docker compose -f ./deploy/local/docker-compose.yaml down celery_worker
	@docker compose -f ./deploy/local/docker-compose.yaml down celery_beat
else ifneq ($(strip $(cont)),)
	@docker rm -f $(cont)
else
	@find . -path '*/migrations/*.pyc'  -delete
	@docker compose -f ./deploy/local/docker-compose.yaml -f ./deploy/local/docker-compose.api_apps.yaml down
	@if [ -n "$$(docker ps -q)" ]; then \
		docker stop $$(docker ps -q); \
	fi
	@if [ -n "$$(docker ps -a -q)" ]; then \
		docker rm $$(docker ps -a -q); \
	fi
	make down-net
endif


rm_venv:
ifeq ($(cont),web)
	@rm -rf $(PWD)/app_web/.venv
else ifeq ($(cont),api)
	@rm -rf $(PWD)/app_api/.venv
else ifneq ($(strip $(cont)),)
	@$(eval VERSION := $(lastword $(subst _, ,$(cont))))
	@$(eval SERVICE := $(patsubst %_$(VERSION),%, $(cont)))
	@echo "Service to remove venv: $(SERVICE)"
	@echo "Version to remove venv: $(VERSION)"
	@rm -rf $(PWD)/app_api/$(SERVICE)/cloud_run_container_$(SERVICE)/$(VERSION)/.venv
else
	@echo "No container specified. Please provide a container name."
endif


create_venv:
ifeq ($(cont),web)
		@if [ -d $(PWD)/app_web/.venv ]; then \
		echo "Activating virtual environment..."; \
		source $(PWD)/app_web/.venv/bin/activate; \
	else \
		echo "Virtual environment not found. Creating a new one..."; \
		python -m venv $(PWD)/app_web/.venv; \
		$(PWD)/app_web/.venv/bin/pip install poetry==1.8.3; \
		$(PWD)/app_web/.venv/bin/poetry env use $(PWD)/app_web/.venv/bin/python; \
		cd $(PWD)/app_web && poetry install --with dev --without container; \
	fi
else ifeq ($(cont),api)
	@if [ -d $(PWD)/app_api/.venv ]; then \
		echo "Activating virtual environment..."; \
		source $(PWD)/app_api/.venv/bin/activate; \
	else \
		echo "Virtual environment not found. Creating a new one..."; \
		python -m venv $(PWD)/app_api/.venv; \
		$(PWD)/app_api/.venv/bin/pip install poetry==1.8.3; \
		$(PWD)/app_api/.venv/bin/poetry env use $(PWD)/app_api/.venv/bin/python; \
		cd $(PWD)/app_api && poetry install; \
	fi
else ifneq ($(strip $(cont)),)
	@$(eval VERSION := $(lastword $(subst _, ,$(cont))))
	@$(eval SERVICE := $(patsubst %_$(VERSION),%, $(cont)))
	@echo "Service to be built: $(SERVICE)"
	@echo "Version to be built: $(VERSION)"
	@if [ -d $(PWD)/app_api/$(SERVICE)/cloud_run_container_$(SERVICE)/$(VERSION)/.venv ]; then \
		echo "Activating virtual environment..."; \
		source $(PWD)/app_api/$(SERVICE)/cloud_run_container_$(SERVICE)/$(VERSION)/.venv/bin/activate; \
	else \
		echo "Virtual environment not found. Creating a new one..."; \
		python -m venv $(PWD)/app_api/$(SERVICE)/cloud_run_container_$(SERVICE)/$(VERSION)/.venv; \
		$(PWD)/app_api/$(SERVICE)/cloud_run_container_$(SERVICE)/$(VERSION)/.venv/bin/pip install poetry==1.8.3; \
		source $(PWD)/app_api/$(SERVICE)/cloud_run_container_$(SERVICE)/$(VERSION)/.venv/bin/activate; \
		poetry env use $(PWD)/app_api/$(SERVICE)/cloud_run_container_$(SERVICE)/$(VERSION)/.venv/bin/python; \
		cd $(PWD)/app_api/$(SERVICE)/cloud_run_container_$(SERVICE)/$(VERSION); \
		if [ ! -f pyproject.toml ]; then \
			echo "No pyproject.toml found. Initializing Poetry project..."; \
			poetry init --name $(SERVICE) --dependency uvicorn --dev-dependency pytest -n; \
		fi; \
		poetry install; \
	fi
else
	@echo "No container specified. Please provide a container name."
endif


clean-docker:
	@read -r -p "ATTENTION !!! This will DELETE all Docker images, volumes and networks. Continue (Y/y)? " ans && \
	[ "$$ans" = "Y" ] || [ "$$ans" = "y" ] || { echo "Cancelled."; exit 1; }; \
	echo "Removing all Docker images, volumes and networks..."; \
	docker rmi -f $$(docker images -q)       2>/dev/null || true; \
	docker volume rm $$(docker volume ls -q) 2>/dev/null || true; \
	docker network rm $$(docker network ls -q) 2>/dev/null || true; \
	docker builder prune --all --force


clean-venvs:
	@read -r -p "ATTENTION !!! This will DELETE every '.venv' directory in this project. Continue (Y/y)? " ans && \
	[ "$$ans" = "Y" ] || [ "$$ans" = "y" ] || { echo "Cancelled."; exit 1; }; \
	echo "Removing all .venv directories..."; \
	find . -type d -name ".venv" -exec rm -rf {} +


bash:
ifeq ($(cont),web)
	@docker exec -it doodleops_web bash
else ifeq ($(cont),api)
	@docker exec -it doodleops_api bash
else ifeq ($(cont),doc)
	@docker exec -it doodleops_doc bash
else ifeq ($(cont),db)
	@docker exec -it doodleops_db bash
else ifeq ($(cont),redis)
	@docker exec -it doodleops_redis bash
else ifeq ($(cont),celery_worker)
	@docker exec -it doodleops_celery_worker bash
else ifeq ($(cont),celery_beat)
	@docker exec -it doodleops_celery_beat bash
else ifeq ($(cont),celery_flower)
	@docker exec -it doodleops_celery_flower bash
else ifneq ($(strip $(cont)),)
	@docker exec -it $(cont) bash
endif


timestamp:
ifeq ($(date),)  # Check if 'date' variable is empty
	@echo "Please provide a date. Example: make timestamp date=01-12-2023"
else
	@python ./scripts/generate_timestamp.py $(date)
endif


mysql:
	docker exec -it doodleops_web bash -c 'mysql -u root -p"$$MYSQL_ROOT_PASSWORD" doodleops_db'

delete_recreate_db:
	@docker exec -it doodleops_web bash -c 'mysql -u root -p"$$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS doodleops_db; CREATE DATABASE doodleops_db;"'


mysql-gcp-dev:
	@echo "Connecting to GCP Cloud SQL Proxy..."
	@echo "Start GCP Cloud SQL Proxy: Tools -> Google Cloud Code -> Google Cloud Database"
	@echo ""
	@echo "Please provide the password for doodleops_user from terraform dev .env file"
	@echo ""
	@mysql -h 127.0.0.1 -u doodleops_user -p doodleops_db

web-run-migrations:
	@echo "Checking if doodleops_db is up..."
	@counter=0; \
	max_counter=180; \
	while true; do \
		if docker exec doodleops_db mysqladmin ping --silent > /dev/null 2>&1; then \
		  	sleep 15; \
			echo "doodleops_db is up. Proceeding..."; \
			break; \
		else \
			echo "Waiting for doodleops_db to be up..."; \
		fi; \
		counter=$$((counter + 1)); \
		if [ $$counter -ge $$max_counter ]; then \
			echo "Waited for 2 minutes. doodleops_db is not up. Exiting..."; \
			exit 1; \
		fi; \
		sleep 1; \
	done
	@docker exec -it doodleops_web python manage.py sqlflush
	@docker exec -it doodleops_web sh -c "find . -path '*/migrations/*.pyc'  -delete"
	@docker exec -it doodleops_web python manage.py dev_reset_db
	@docker exec -it doodleops_web python manage.py makemigrations
	@docker exec -it doodleops_web python manage.py migrate

web-populate-dummy-data:
	docker exec -it doodleops_web python manage.py dev_populate_app_settings
	docker exec -it doodleops_web python manage.py dev_populate_pricing_tables
	docker exec -it doodleops_web python manage.py dev_populate_users
	docker exec -it doodleops_web python manage.py dev_populate_api_counter
	docker exec -it doodleops_web python manage.py dev_populate_apis


run:
ifeq ($(cont),web)
	@docker exec -it doodleops_web sh -c "DEBUG=true OPENTELEMETRY_SERVICE_NAME=django-app-runserver python manage.py runserver 0.0.0.0:8000"
else ifeq ($(cont),gunicorn)
	@docker exec -it doodleops_web sh -c "DEBUG=true OPENTELEMETRY_SERVICE_NAME=django-app-gunicorn PORT=8000 gunicorn core.wsgi:application --config=gunicorn_conf.py"
else ifeq ($(cont),api)
	@docker exec -it doodleops_api sh -c "PORT=9000 python uvicorn_config.py"
else ifeq ($(cont),celery_worker)
	@docker exec -it doodleops_celery_worker sh -c "OPENTELEMETRY_SERVICE_NAME=celery-worker celery -A core worker --loglevel=info"
else ifeq ($(cont),celery_beat)
	@docker exec -it doodleops_celery_beat sh -c "OPENTELEMETRY_SERVICE_NAME=celery-beat celery -A core beat --loglevel=info"
else ifeq ($(cont),celery_flower)
	@docker exec -it doodleops_celery_flower sh -c "celery -A core flower --loglevel=debug --address=0.0.0.0 --port=5555"
else ifneq ($(strip $(cont)),)
	@docker exec -it $(cont) sh -c "python uvicorn_config.py"
endif


stripe-webhook:
	@stripe listen --forward-to http://127.0.0.1:8000/financial/stripe-webhook/


update-pre-commit:
	@cp scripts/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit


terra-update-secrets:
ifeq ($(cont),web)
	@terraform -chdir=deploy/cloud/terraform/dev/ apply -target=google_secret_manager_secret_version.app-web
else ifeq ($(cont),api)
	@terraform -chdir=deploy/cloud/terraform/dev/ apply -target=google_secret_manager_secret_version.app-api
else ifeq ($(cont),api_apps)
	@terraform -chdir=deploy/cloud/terraform/dev/ apply -target=google_secret_manager_secret_version.app-api-apps
else ifneq ($(strip $(cont)),)
	@echo "Updating secrets for $(cont)"
endif


terra-plan:
ifeq ($(GCP_PROJECT_ID),doodleops-dev)
	@terraform -chdir=deploy/cloud/terraform/dev/ plan
else ifeq ($(GCP_PROJECT_ID),doodleops-prod)
	@terraform -chdir=deploy/cloud/terraform/prod/ plan
endif


terra-apply:
ifeq ($(GCP_PROJECT_ID),doodleops-dev)
	@terraform -chdir=deploy/cloud/terraform/dev/ apply
else ifeq ($(GCP_PROJECT_ID),doodleops-prod)
	@terraform -chdir=deploy/cloud/terraform/prod/ apply
endif


help:
	@printf "\n\033[1mUsage:\033[0m  make <target> [VARIABLE=value …]\n\n"

	@printf "\033[1mCore targets\033[0m\n"
	@printf "  %-22s – %-42s %s\n" "status"   "List all Docker containers"                "make status"
	@printf "  %-22s – %-42s %s\n" "up"       "Start containers"                           "make up cont=api"
	@printf "  %-22s – %-42s %s\n" "down"     "Stop / remove containers"                   "make down cont=web"
	@printf "  %-22s – %-42s %s\n" "build"    "Build images"                               "make build cont=app_docs_v1"
	@printf "  %-22s – %-42s %s\n" "bash"     "Open shell in running container"             "make bash cont=api"
	@printf "  %-22s – %-42s %s\n" "run"      "Run local server / worker in container"       "make run cont=web"

	@printf "\n\033[1mHouse-keeping\033[0m\n"
	@printf "  %-22s – %-42s %s\n" "clean-docker"   "⚠️  Delete ALL Docker images & volumes"        "make clean-docker"
	@printf "  %-22s – %-42s %s\n" "clean-venvs"    "⚠️  Delete every .venv in repo"                "make clean-venvs"
	@printf "  %-22s – %-42s %s\n" "rm_venv"        "Remove .venv for one component"           "make rm_venv cont=app_docs_v1"
	@printf "  %-22s – %-42s %s\n" "create_venv"    "Create/activate .venv for component"      "make create_venv cont=api"

	@printf "\n\033[1mDatabase & migrations\033[0m\n"
	@printf "  %-22s – %-42s %s\n" "mysql"                "Open MySQL client inside doodleops_web" "make mysql"
	@printf "  %-22s – %-42s %s\n" "delete_recreate_db"   "Drop & recreate local DB"               "make delete_recreate_db"
	@printf "  %-22s – %-42s %s\n" "web-run-migrations"   "Flush DB + re-run migrations"           "make web-run-migrations"
	@printf "  %-22s – %-42s %s\n" "web-populate-dummy-data" "Load demo data"                       "make web-populate-dummy-data"

	@printf "\n\033[1mTerraform & secrets\033[0m\n"
	@printf "  %-22s – %-42s %s\n" "terra-plan"          "Terraform plan (auto-detect env)"       "make terra-plan"
	@printf "  %-22s – %-42s %s\n" "terra-apply"         "Terraform apply"                        "make terra-apply"
	@printf "  %-22s – %-42s %s\n" "terra-update-secrets" "Push latest secrets to Secret Manager" "make terra-update-secrets cont=web"

	@printf "\n\033[1mMisc\033[0m\n"
	@printf "  %-22s – %-42s %s\n" "stripe-webhook"      "Start Stripe CLI forwarder"             "make stripe-webhook"
	@printf "  %-22s – %-42s %s\n" "timestamp"           "Generate Unix timestamp"                "make timestamp date=01-12-2025"
	@printf "  %-22s – %-42s %s\n" "update-pre-commit"   "Copy pre-commit hook"                   "make update-pre-commit"

	@printf "\n\033[1mEnvironment variables\033[0m\n"
	@printf "  %-22s – %-42s %s\n" "  cont=api | web | app_docs_v1 | ...    choose which container/service"
	@printf "  %-22s – %-42s %s\n" "  mode=local | dev | prod             environment mode for compose targets"
	@printf ""

	@printf "\n"
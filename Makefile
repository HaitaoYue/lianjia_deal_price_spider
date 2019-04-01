export DEV?=True
export RELEASE?=False
SLASH:=/
REPLACE_SLASH:=\/
export ROOT_PATH = ${PWD}
ROOT_PATH_REPLACE=$(subst $(SLASH),$(REPLACE_SLASH),$(ROOT_PATH))
export ARCH = $(shell arch)
DOCKER=`which docker`

-include .makerc/help
-include .makerc/docker
-include .makerc/deploy
-include .makerc/command
-include .makerc/k8s
-include .makerc/output

build-binary:
	bash scripts/build_binary/run.sh

build-image-prod:
	@$(MAKE) -C docker/$(ARCH) all

build-image-release:
	docker build -t $(PORTAL_IMAGE_NAME) -f docker/$(ARCH)/build_classify/Dockerfile-release .
	docker build -t $(NGINX_IMAGE_NAME) -f docker/$(ARCH)/build_nginx/Dockerfile .

check-ns:
	@kubectl get ns/$(K8S_DEPLOY_NAMESPACE) || kubectl create ns $(K8S_DEPLOY_NAMESPACE)

build-image-dev:
	@$(MAKE) -C docker/$(ARCH) all

build-image: ##@Docker Build essential docker images for this service.
	@$(MAKE) $(BUILD_IMAGE)

clean-images: ##@Docker Clean images that dangling.
	$(DOCKER) rmi -f ${SERVER_IMAGE} ${NGINX_IMAGE}
	$(DOCKER) rmi -f `docker images -f "dangling=true" -q`

check: ##Code check code
	tox

initial-env: ##@Configuration Initial Configuration for horizon service.
	@envsubst < env.tmpl > .env

init:
	sudo mkdir -p ${GRAFANA_PATH} && sudo chmod a+w ${GRAFANA_PATH}
	echo "Initializing..."
	@envsubst < docker-compose-files/init/docker-compose.yml.tmpl > docker-compose-files/init/docker-compose.yml
	docker-compose -f docker-compose-files/init/docker-compose.yml up --force-recreate --abort-on-container-exit
	echo "Done"

create-db-secret: ##@kubernetes create secret for store password
	@kubectl create secret generic $(K8S_DB_SECRET_NAME) \
		--from-literal=username='${MONGO_USER}' --from-literal=password='${MONGO_PASSWORD}' -n ${K8S_DEPLOY_NAMESPACE}

create-docker-secret: ##@kubernetes create secret for private docker repo
	@kubectl create secret docker-registry $(DOCKER_SECRET_NAME) \
		--docker-server=$(DOCKER_REPO_HOST) --docker-username=$(DOCKER_REPO_USERNAME) \
		--docker-password=$(DOCKER_REPO_PASSWORD) --docker-email=$(DOCKER_REPO_EMAIL) -n ${K8S_DEPLOY_NAMESPACE}

WHO=$(shell whoami)

init-yaml:
	@envsubst < env.tmpl > .env

start: ##@Docker Start docker services with docker-compose files. Change the variable in the .env file under different circumstances.
	@$(MAKE) init-yaml
	docker-compose -f bootup/docker-compose.yml up -d

stop:
	docker-compose -f bootup/docker-compose.yml down

test-api:
	@$(MAKE) -C postman/ test-api

restart-uwsgi: ##@uWsgi Restart uWsgi server
	bash scripts/uwsgi-docker.sh restart-uwsgi

log-uwsgi: ##@uWsgi Watch uWsgi log
	bash scripts/uwsgi-docker.sh log-uwsgi

enter-uwsgi: ##@uWsgi Enter uWsgi container bash
	bash scripts/uwsgi-docker.sh enter-uwsgi

generate-api-yaml: ##@uWsgi Generate api yaml file
	bash scripts/uwsgi-docker.sh generate-api-yaml

generate-swagger: ##@swagger Generate swagger markdown & redoc html file
	@$(MAKE) generate-api-yaml
	docker-compose -f bootup/docker-compose/swagger-generator/swagger-api.yaml up

generate-model-graph: ##@uWsgi Generate model graph
	bash scripts/uwsgi-docker.sh generate-model-graph

migrate-db: ##@uWsgi migrate database
	bash scripts/uwsgi-docker.sh migrate-db

HELP_FUN = \
	%help; \
	while(<>) { push @{$$help{$$2 // 'options'}}, [$$1, $$3] if /^([a-zA-Z\-]+)\s*:.*\#\#(?:@([a-zA-Z\-]+))?\s(.*)$$/ }; \
	print "usage: make [target]\n\n"; \
	for (sort keys %help) { \
	print "${WHITE}$$_:${RESET}\n"; \
	for (@{$$help{$$_}}) { \
	$$sep = " " x (32 - length $$_->[0]); \
	print "  ${YELLOW}$$_->[0]${RESET}$$sep${GREEN}$$_->[1]${RESET}\n"; \
	}; \
	print "\n"; }

help: ##@other Show this help.
	@perl -e '$(HELP_FUN)' $(MAKEFILE_LIST)
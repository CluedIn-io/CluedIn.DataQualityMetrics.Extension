# Container registry and image. Override on the command line or in the environment:
#   make docker-push REGISTRY=myregistry.azurecr.io
REGISTRY ?= localhost:5000
IMAGE ?= cluedin-data-quality-metrics-extension
TAG ?= latest
PLATFORM ?= linux/amd64

# Kubernetes target.
NAMESPACE ?= cluedin
RELEASE ?= cluedin-data-quality-metrics-extension
PULL_SECRET ?= registry-key

# Local run.
CONFIG ?= config/metrics.json
VALUES ?= values.local.yaml

.PHONY: run validate dry-run venv requirements docker-build docker-push helm \
        helm-install create-pull-secret create-metrics-secret

run:
		python metrics.py --config $(CONFIG)

validate:
		python metrics.py --config $(CONFIG) --validate

dry-run:
		python metrics.py --config $(CONFIG) --dry-run

venv:
		virtualenv venv && . venv/bin/activate

requirements:
		pip install -r requirements.txt

docker-build:
		docker buildx build --platform=$(PLATFORM) -t $(REGISTRY)/$(IMAGE):$(TAG) .

docker-push: docker-build
		docker push $(REGISTRY)/$(IMAGE):$(TAG)

# Renders the chart without applying it. Drop --dry-run, or use helm-install.
helm:
		helm upgrade $(RELEASE) ./helm --install --history-max 3 \
				--namespace $(NAMESPACE) \
				--set image.repository=$(REGISTRY)/$(IMAGE) \
				--set image.tag=$(TAG) \
				--values $(VALUES) \
				--dry-run

helm-install:
		helm upgrade $(RELEASE) ./helm --install --history-max 3 \
				--namespace $(NAMESPACE) \
				--set image.repository=$(REGISTRY)/$(IMAGE) \
				--set image.tag=$(TAG) \
				--values $(VALUES)

create-pull-secret:
		kubectl create secret docker-registry $(PULL_SECRET) \
				--namespace $(NAMESPACE) \
				--docker-server=$(REGISTRY) \
				--docker-username=$(REGISTRY_USERNAME) \
				--docker-password=$(REGISTRY_PASSWORD)

create-metrics-secret:
		kubectl create secret generic $(RELEASE) \
				--namespace $(NAMESPACE) \
				--from-literal=access_token=$(CLUEDIN_ACCESS_TOKEN) \
				--from-literal=sql_server=$(METRICS_SQL_SERVER) \
				--from-literal=sql_database=$(METRICS_SQL_DATABASE) \
				--from-literal=sql_user=$(METRICS_SQL_USER) \
				--from-literal=sql_password=$(METRICS_SQL_PASSWORD) \
				--from-literal=metrics_table=$(METRICS_TABLE)

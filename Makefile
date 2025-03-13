# vars
PYTHON_VERSION = 3.11
BIN = .venv/bin
ACTIVATE = . $(BIN)/activate &&
PYTHON = $(ACTIVATE) python
PIP = $(ACTIVATE) uv pip
COMPILE = $(ACTIVATE) uv pip compile

# development
venv:
	@uv venv -p $(PYTHON_VERSION)
	$(PIP) install -U pip

install-prod:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r dev-requirements.txt

install: venv install-prod install-dev

format:
	@$(ACTIVATE) ruff format src --preview

lint:
	@$(ACTIVATE) ruff check src --fix --preview

up:
	@$(ACTIVATE) AWS_PROFILE=$(PROFILE) pulumi up --stack juno

down:
	@$(ACTIVATE) AWS_PROFILE=$(PROFILE) pulumi destroy --stack juno

refresh:
	@$(ACTIVATE) PULUMI_K8S_DELETE_UNREACHABLE=true AWS_PROFILE=$(PROFILE) pulumi refresh --stack juno

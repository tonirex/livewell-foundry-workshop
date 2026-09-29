# LiveWell workshop tasks. Run here (make validate) or from the repo root (make -C content/assets validate).
# Phase 4 adds: notebooks (jupytext -> untracked .ipynb) and clean-agents.
ROOT   := $(abspath ../..)
PYTHON ?= python
ENV    ?=
RUNS   ?= 3

.PHONY: help validate validate-live fill

help:
	@echo "make validate        content checks + narrative gate static/data layers (no Azure needed)"
	@echo "make validate-live   all layers: + graph check and RUNS=$(RUNS) data-agent calls per question (ENV=<azd env>)"
	@echo "make fill            recompute reference answers and refill the {{ref:...}} values in story and lab pages"

validate:
	cd "$(ROOT)" && $(PYTHON) scripts/check-content.py
	cd "$(ROOT)" && $(PYTHON) scripts/validate-narrative.py --layers static,data --check --no-report

validate-live:
	cd "$(ROOT)" && $(PYTHON) scripts/validate-narrative.py --layers all --runs $(RUNS) $(if $(ENV),--env $(ENV))

fill:
	cd "$(ROOT)" && $(PYTHON) scripts/validate-narrative.py --layers static,data --fill --no-report

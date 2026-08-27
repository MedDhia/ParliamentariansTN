PY ?= python3
export PYTHONPATH := src

.PHONY: help all collect build validate networks codebook test clean-cache reference \
        collect-arp collect-anc collect-arp2014 collect-majles collect-wiki

help:
	@echo "ParliamentariansTN"
	@echo ""
	@echo "  make all        build + validate + networks + codebook (no network access)"
	@echo "  make collect    run every collector (hits upstream; ~15 min, rate-limited)"
	@echo "  make build      merge staging documents into data/processed"
	@echo "  make validate   schema, referential integrity, date and substance checks"
	@echo "  make networks   derive data/networks"
	@echo "  make codebook   regenerate docs/CODEBOOK.md and docs/COVERAGE.md"
	@echo "  make test       run unit tests"
	@echo "  make reference  rewrite data/reference from reference.py"
	@echo ""
	@echo "  Individual collectors: collect-arp collect-anc collect-arp2014 collect-majles collect-wiki"
	@echo "  Add REFRESH=1 to bypass the raw cache."

REFRESH_FLAG := $(if $(REFRESH),--refresh,)

all: build validate networks codebook

collect: collect-wiki collect-anc collect-arp2014 collect-majles collect-arp

collect-arp:
	$(PY) -m parliamentarians_tn.collect.arp_odoo $(REFRESH_FLAG)

collect-anc:
	$(PY) -m parliamentarians_tn.collect.marsad_anc $(REFRESH_FLAG)

collect-arp2014:
	$(PY) -m parliamentarians_tn.collect.marsad_arp2014 $(REFRESH_FLAG)

collect-majles:
	$(PY) -m parliamentarians_tn.collect.marsad_majles $(REFRESH_FLAG)

collect-wiki:
	$(PY) -m parliamentarians_tn.collect.wikipedia_anc1956 $(REFRESH_FLAG)

reference:
	$(PY) -m parliamentarians_tn.reference

build: reference
	$(PY) -m parliamentarians_tn.build

validate:
	$(PY) -m parliamentarians_tn.validate

networks:
	$(PY) -m parliamentarians_tn.networks

codebook:
	$(PY) -m parliamentarians_tn.codebook

test:
	$(PY) -m pytest tests -q

# Drops cached upstream pages but keeps the staging documents, so `make build`
# still works offline afterwards.
clean-cache:
	find data/raw -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
	@echo "cached upstream pages removed; staging documents kept"

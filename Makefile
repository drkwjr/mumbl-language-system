.PHONY: bootstrap setup-packages check-deps check fmt test unit integration e2e clean generate-schemas generate-types build-admin-ui admin-ui stop-admin-ui run-api

bootstrap:
	bash scripts/bootstrap_env.sh
	pip install -e packages/data-contracts/python
	pip install -e packages/format-guardians/python
	pip install -e packages/dataset-builder/python
	pip install -e packages/orchestration/python
	cd apps/admin-ui && npm i || true

setup-packages:
	bash scripts/setup_all_packages.sh

check-deps:
	python scripts/check_dependencies.py

check:
	rufflehog --version >/dev/null 2>&1 || true
	python -m mumbl_dataset_builder.tools.dataset_build --help >/dev/null 2>&1 || true
	python -m mumbl_format_guardians.tools.profile_validate --help >/dev/null 2>&1 || true
	# add linters here as they are introduced

fmt:
	# TODO: add black/isort/ruff/prettier

test: unit integration

unit:
	pytest -q tests/unit

integration:
	pytest -q tests/integration

e2e:
	pytest -q tests/e2e

clean:
	rm -rf .venv
	rm -rf apps/admin-ui/node_modules
	rm -rf packages/data-contracts/typescript/dist
	rm -rf packages/data-contracts/typescript/node_modules

generate-schemas:
	python scripts/generate_schemas.py

generate-types:
	python scripts/generate_typescript_types.py

build-admin-ui:
	cd apps/admin-ui && npm run build

build-contracts:
	cd packages/data-contracts/typescript && npm run build

# Start admin UI with full setup and browser opening
admin-ui:
	./scripts/start_admin_ui.sh

# Stop admin UI processes
stop-admin-ui:
	./scripts/stop_admin_ui.sh

run-api:
	uvicorn apps.runtime.api:app --reload --host 0.0.0.0 --port 8000

# Database management
setup-db:
	./infra/db/setup_db.sh

db-connect:
	PGPASSWORD=mumbl_dev_password psql -U mumbl_user -d mumbl_lang_system

db-reset:
	PGPASSWORD=mumbl_dev_password psql -U mumbl_user -d mumbl_lang_system -c "TRUNCATE text_segments, audio_segments, segment_scores, raw_artifacts CASCADE;"

# Text Lane
install-text-lane:
	pip install -e apps/text-lane

test-text-lane:
	python -c "from text_lane.processor import TextLaneProcessor; print('✓ Text Lane installed')"

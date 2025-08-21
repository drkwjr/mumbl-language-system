.PHONY: bootstrap check fmt test clean generate-schemas generate-types build-admin-ui admin-ui stop-admin-ui

bootstrap:
	bash scripts/bootstrap_env.sh
	cd apps/admin-ui && npm i || true

check:
	rufflehog --version >/dev/null 2>&1 || true
	# add linters here as they are introduced

fmt:
	# placeholder for black, isort, prettier

test:
	pytest -q

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

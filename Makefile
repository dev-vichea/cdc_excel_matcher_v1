.PHONY: run start stop restart logs build clean

# Start app in Docker (builds if needed and opens in browser)
run:
	@./run_docker.sh

start:
	@docker compose up -d
	@echo "CDC Customs Manager running at http://localhost:8501"

stop:
	@./stop_docker.sh

restart:
	@docker compose restart
	@echo "Restarted container"

logs:
	@docker compose logs -f

build:
	@docker compose build

clean:
	@docker compose down -v --rmi local


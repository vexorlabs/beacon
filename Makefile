# =============================================================================
# Beacon — Root Makefile
# =============================================================================

PYTHON       := python3
VENV         := backend/.venv
PIP          := $(VENV)/bin/pip
BACKEND_DIR  := backend
FRONTEND_DIR := frontend
SDK_DIR      := sdk
BACKEND_PORT := 7474
FRONTEND_PORT := 5173
DB_PATH      := $(HOME)/.beacon/traces.db

.PHONY: help install dev dev-backend dev-frontend stop test lint format clean db-reset

help:
	@echo ""
	@echo "Beacon — available targets:"
	@echo ""
	@echo "  Setup:"
	@echo "    make install        Create venv and install all dependencies"
	@echo ""
	@echo "  Dev:"
	@echo "    make dev            Start backend + frontend (Ctrl-C to stop both)"
	@echo "    make dev-backend    Start backend only (port $(BACKEND_PORT))"
	@echo "    make dev-frontend   Start frontend only (port $(FRONTEND_PORT))"
	@echo ""
	@echo "  Stop:"
	@echo "    make stop           Kill processes on ports $(BACKEND_PORT) and $(FRONTEND_PORT)"
	@echo ""
	@echo "  Quality:"
	@echo "    make test           Run backend + SDK tests"
	@echo "    make lint           Run all linters"
	@echo "    make format         Run all formatters"
	@echo ""
	@echo "  Utilities:"
	@echo "    make clean          Remove venvs, node_modules, build artifacts"
	@echo "    make db-reset       Delete ~/.beacon/traces.db"
	@echo ""

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

install:
	@echo "--- Creating backend venv ---"
	$(PYTHON) -m venv $(VENV)
	@echo "--- Installing backend dependencies ---"
	$(PIP) install -e "$(BACKEND_DIR)[dev]"
	@echo "--- Installing SDK (editable, into backend venv) ---"
	$(PIP) install -e "$(SDK_DIR)[dev]"
	@echo "--- Installing frontend dependencies ---"
	npm --prefix $(FRONTEND_DIR) install
	@echo ""
	@echo "Done. Run 'make dev' to start."

# -----------------------------------------------------------------------------
# Dev servers
# -----------------------------------------------------------------------------

dev:
	@echo "Starting backend (port $(BACKEND_PORT)) and frontend (port $(FRONTEND_PORT)) ..."
	@echo "Press Ctrl-C to stop both."
	@trap 'kill $$BACKEND_PID $$FRONTEND_PID 2>/dev/null; exit 0' INT TERM; \
	  $(VENV)/bin/uvicorn app.main:app --reload --port $(BACKEND_PORT) --app-dir $(BACKEND_DIR) & BACKEND_PID=$$!; \
	  npm --prefix $(FRONTEND_DIR) run dev & FRONTEND_PID=$$!; \
	  wait $$BACKEND_PID $$FRONTEND_PID

dev-backend:
	$(VENV)/bin/uvicorn app.main:app --reload --port $(BACKEND_PORT) --app-dir $(BACKEND_DIR)

dev-frontend:
	npm --prefix $(FRONTEND_DIR) run dev

# -----------------------------------------------------------------------------
# Stop
# -----------------------------------------------------------------------------

stop:
	@echo "Stopping processes on ports $(BACKEND_PORT) and $(FRONTEND_PORT) ..."
	@lsof -ti :$(BACKEND_PORT) | xargs kill 2>/dev/null || true
	@lsof -ti :$(FRONTEND_PORT) | xargs kill 2>/dev/null || true
	@echo "Done."

# -----------------------------------------------------------------------------
# Testing and quality
# -----------------------------------------------------------------------------

test:
	@echo "--- Backend tests ---"
	$(VENV)/bin/pytest $(BACKEND_DIR)/tests -v
	@echo "--- SDK tests ---"
	$(VENV)/bin/pytest $(SDK_DIR)/tests -v

lint:
	@echo "--- Python: black (check) ---"
	$(VENV)/bin/black --check $(BACKEND_DIR)/app $(SDK_DIR)/beacon_sdk
	@echo "--- Python: isort (check) ---"
	$(VENV)/bin/isort --check-only --profile black $(BACKEND_DIR)/app $(SDK_DIR)/beacon_sdk
	@echo "--- TypeScript: eslint ---"
	npm --prefix $(FRONTEND_DIR) run lint

format:
	@echo "--- Python: black ---"
	$(VENV)/bin/black $(BACKEND_DIR)/app $(SDK_DIR)/beacon_sdk
	@echo "--- Python: isort ---"
	$(VENV)/bin/isort --profile black $(BACKEND_DIR)/app $(SDK_DIR)/beacon_sdk

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

clean:
	rm -rf $(VENV)
	rm -rf $(FRONTEND_DIR)/node_modules
	rm -rf $(FRONTEND_DIR)/dist
	rm -rf $(BACKEND_DIR)/__pycache__ $(BACKEND_DIR)/app/__pycache__
	find $(SDK_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(SDK_DIR) -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete."

db-reset:
	@if [ -f "$(DB_PATH)" ]; then \
	  rm "$(DB_PATH)"; \
	  echo "Deleted $(DB_PATH)"; \
	else \
	  echo "No database found at $(DB_PATH)"; \
	fi

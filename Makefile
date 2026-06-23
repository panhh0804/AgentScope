.PHONY: help backend frontend simulator-sample

help:
	@echo "AgentScope commands:"
	@echo "  make backend           Start FastAPI dev server"
	@echo "  make frontend          Start Vue dev server"
	@echo "  make simulator-sample  Generate local JSONL sample events"

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev -- --host 0.0.0.0 --port 5173

simulator-sample:
	mkdir -p tmp
	cd simulator && python main.py --mode offline --count 100 --output ../tmp/agent_events.jsonl


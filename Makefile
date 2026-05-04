.PHONY: help run new resume auto clean-db clean-outputs clean logs lint fmt typecheck test

PYTHON := python3
MAIN   := src/main.py
DB     := it_team.db
VENV   := .venv/bin

help:
	@echo "Usage: make <target> [TASK='...']"
	@echo ""
	@echo "  run            Resume last incomplete task, or prompt for new one"
	@echo "  new            Start a new task (cancel any incomplete ones)"
	@echo "  new TASK='..'  Start a new task inline, no prompt"
	@echo "  resume         Resume last incomplete/failed task (alias for run)"
	@echo "  auto           Run fully automated (HUMAN_IN_THE_LOOP=False)"
	@echo "  auto TASK='..'   Run automated with inline task"
	@echo "  copilot        Run with GitHub Copilot as LLM (gpt-4o via Copilot API)"
	@echo "  copilot TASK='..'  Copilot provider with inline task"
	@echo "  logs           Show context change log for the last task"
	@echo "  clean-db       Delete the SQLite database (full reset)"
	@echo "  clean-outputs  Delete generated outputs and code"
	@echo "  clean          clean-db + clean-outputs"

run:
	$(PYTHON) $(MAIN)

resume:
	$(PYTHON) $(MAIN)

new:
ifdef TASK
	$(PYTHON) $(MAIN) --new "$(TASK)"
else
	$(PYTHON) $(MAIN) --new
endif

auto:
ifdef TASK
	HUMAN_IN_THE_LOOP=False $(PYTHON) $(MAIN) --new "$(TASK)"
else
	HUMAN_IN_THE_LOOP=False $(PYTHON) $(MAIN)
endif

copilot:
ifdef TASK
	LLM_PROVIDER=copilot LLM_MODEL=gpt-4o HUMAN_IN_THE_LOOP=False $(PYTHON) $(MAIN) --new "$(TASK)"
else
	LLM_PROVIDER=copilot LLM_MODEL=gpt-4o HUMAN_IN_THE_LOOP=False $(PYTHON) $(MAIN)
endif

logs:
	@$(PYTHON) -c "\
import sys; sys.path.insert(0, 'src'); \
from database import init_db, get_conn; init_db(); \
from config import DB_PATH; \
import sqlite3, json; \
conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; \
task = conn.execute('SELECT * FROM tasks ORDER BY id DESC LIMIT 1').fetchone(); \
print(f'Task #{task[\"id\"]} [{task[\"status\"]}]: {task[\"user_input\"][:80]}'); \
print('-'*60); \
rows = conn.execute('SELECT * FROM context_log WHERE task_id=? ORDER BY id', (task['id'],)).fetchall(); \
[print(f'  [{r[\"timestamp\"]}] iter={r[\"iteration\"]} {r[\"agent\"]:12s} {r[\"field\"]:20s} -> {(r[\"new_value\"] or \"-\")[:80]}') for r in rows] \
"

clean-db:
	@echo "Deleting $(DB)..."
	rm -f $(DB)
	@echo "Done."

clean-outputs:
	@echo "Deleting outputs/ and generated/..."
	rm -rf outputs/ generated/
	@echo "Done."

clean: clean-db clean-outputs

lint:
	$(VENV)/ruff check .

fmt:
	$(VENV)/ruff format .

typecheck:
	$(VENV)/mypy . --exclude '\.venv'

test:
	$(VENV)/pytest

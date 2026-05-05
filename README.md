# 🤖 LangGraph IT Team

A multi-agent system that simulates a full IT backend team using [LangGraph](https://github.com/langchain-ai/langgraph). You describe a backend task — the agents design, implement, test, review, validate, and deploy it.

## Pipeline

```
product_manager
      │
teamlead_decompose
      │
  architect
      │
qa_test_design   ← writes tests first (TDD)
      │
  developer ◄─────────────────────────────────────┐
      │                                            │
  reviewer ──── "rework" ──────────────────────────┤
      │                                            │
      └── "approved"                               │
            │                                      │
      qa_validation ──── "fail" ───────────────────┤
            │                                      │
            └── "pass"                             │
                  │                                │
            ci_validator ──── "fail" ──────────────┘
                  │
                  └── "pass"
                        │
                    jira_setup
                        │
                      devops
                        │
                teamlead_summarize
```

Each agent plays a specific role:

| Agent | Role |
|-------|------|
| `product_manager` | Clarifies requirements and acceptance criteria |
| `teamlead_decompose` | Breaks task into subtasks |
| `architect` | Designs the technical solution |
| `qa_test_design` | Writes tests upfront (TDD) |
| `developer` | Implements the code |
| `reviewer` | Reviews code quality, approves or requests rework |
| `qa_validation` | Validates tests pass against the implementation |
| `ci_validator` | Simulates CI: linting, build, test run |
| `jira_setup` | Creates Jira tickets |
| `devops` | Generates deployment config |
| `teamlead_summarize` | Produces final delivery summary |

## Requirements

- Python 3.12+
- [gh CLI](https://cli.github.com/) (for GitHub Copilot provider)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Secrets

Create `~/.agent_keys/secrets.json`:

```json
{
  "groq": { "api_key": "gsk_..." },
  "anthropic": "sk-ant-...",
  "jira": {
    "base_url": "https://your-org.atlassian.net",
    "email": "you@example.com",
    "api_token": "..."
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `groq` | `groq` / `anthropic` / `copilot` |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Model name for the chosen provider |
| `LLM_TEMPERATURE` | `0.3` | Sampling temperature |
| `MAX_REVIEW_ITERATIONS` | `5` | Max developer/reviewer/QA cycles |
| `HUMAN_IN_THE_LOOP` | `True` | Pause for confirmation between steps |
| `AGENT_TIMEOUT` | `3000` | Timeout per agent call (seconds) |
| `DB_PATH` | `it_team.db` | SQLite database path |

## Usage

```bash
# Prompt for task interactively
make run

# New task inline
make new TASK="Create a REST API for user authentication with JWT"

# Resume last incomplete/failed task
make resume

# Run fully automated (no human confirmations)
make auto TASK="Create a REST API for user authentication with JWT"

# Use GitHub Copilot as LLM (gpt-4o)
make copilot TASK="Create a CRUD service for blog posts"

# View context change log for the last task
make logs
```

Or run directly:

```bash
python src/main.py "Create a REST API for user authentication with JWT"
python src/main.py --new "task"
python src/main.py --project-dir /path/to/project "task"
python src/main.py --new --task-file task.txt
python src/main.py --new --task-editor   # opens $EDITOR
```

### Resume Support

If a run is interrupted or fails, the pipeline saves a checkpoint. On the next run you'll be prompted to resume from the last completed step — no need to restart from scratch.

## Development

```bash
make lint       # ruff check
make fmt        # ruff format
make typecheck  # mypy
make test       # pytest

make clean      # delete DB + generated outputs
make clean-db   # delete only the DB
```

## Project Structure

```
src/
├── agents/          # One file per agent
│   ├── product_manager.py
│   ├── teamlead.py
│   ├── architect.py
│   ├── qa.py
│   ├── qa_validation.py
│   ├── developer.py
│   ├── reviewer.py
│   ├── ci_validator.py
│   ├── jira.py
│   └── devops.py
├── llm/             # LLM factory (groq / anthropic / copilot)
├── graph.py         # LangGraph pipeline definition
├── state.py         # Shared state schema
├── config.py        # Configuration & secrets loader
├── database.py      # SQLite persistence & checkpointing
└── main.py          # Entry point
tests/               # pytest test suite
```

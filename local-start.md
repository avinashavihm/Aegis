# Local start guide (API + CLI)

## 1) Start the API locally (no Docker)
```bash
cd aegis-service
uv venv
source .venv/bin/activate
uv pip install -e .

DB_HOST=localhost \
DB_PORT=5432 \
DB_NAME=agentic_ops \
DB_USER=aegis_app \
DB_PASSWORD=password123 \
./.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## 2) Start the API with Docker Compose
```bash
docker compose up -d
# postgres on 5432, api on 8000
```

## 3) Install and use the CLI (aegis-cli/aegis-cli)
```bash
cd aegis-cli/aegis-cli
uv venv
source .venv/bin/activate
uv pip install -e .

export AEGIS_API_URL=http://localhost:8000
aegis login --username root -p admin

# create an agent (prints the agent UUID)
aegis agent create research-agent --desc "research agent that can web scrap and do detailed research on any topic" --tools web_search

# run the agent (use the printed UUID or fetch it)
aegis agent run <agent-uuid> "Hello from CLI" -w
# to fetch the UUID later
aegis agent get research-agent --output json
```

## 4) Quick clean-up
```bash
aegis agent delete research-agent -y    # remove demo agent
docker compose down                     # stop containers (if using compose)
```

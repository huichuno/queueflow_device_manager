# How to run *test_api_server.py*
## Pre-requisite
Make sure following are running:
1. MCP server
2. AI Agent
3. LLM model server (Ollama with IPEX LLM)

```sh
cd queueflow_device_manager

# start MCP server
uv run tests/mock_queue_flow_mgmt.py

# start AI Agent
uv run main.py
# or, "uv run adk api_server --port 9091 --host 0.0.0.0"

# run test
uv run pytest

```

# Troubleshooting
## How to start a sesssion with adk api_server
```sh
curl -X POST http://localhost:9091/apps/queueflow_device_manager/users/u_123/sessions/s_123 \
  -H "Content-Type: application/json" \
  -d '{"state": {"key1": "value1", "key2": 42}}'
```

## How to post a query
```sh
curl -X POST http://localhost:9091/run \
-H "Content-Type: application/json" \
-d '{
"app_name": "queueflow_device_manager",
"user_id": "u_123",
"session_id": "s_123",
"new_message": {
    "role": "user",
    "parts": [{
    "text": "list all the supported tools" 
    }]
}
}'
```

## How to post a query with streaming response
```sh
curl -X POST http://localhost:9091/run_sse \
-H "Content-Type: application/json" \
-d '{
"app_name": "queueflow_device_manager",
"user_id": "u_123",
"session_id": "s_123",
"new_message": {
    "role": "user",
    "parts": [{
    "text": "list all the supported tools" 
    }]
},
"streaming": true
}'
```
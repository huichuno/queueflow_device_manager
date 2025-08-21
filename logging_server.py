import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

logging_dir = os.path.dirname(os.path.abspath(__file__))
queue_management_dir = os.path.join(logging_dir, "mcp", "queue_flow_mgmt")
log_path = os.path.join(queue_management_dir, "qflow.log")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def log_stream():
    try:
        with open(log_path, 'r') as log_file:
            for line in log_file:
                yield line.strip() + "\n"
    except Exception as e:
        yield f"Error reading log file: {e}\n" + "===========================================================\n"

@app.get("/stream_log")
def stream():
    return StreamingResponse(log_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9090)
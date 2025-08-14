import os
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

app = get_fast_api_app(
    agents_dir=os.path.dirname(os.path.abspath(__file__)),
    allow_origins=["http://localhost", "http://localhost:9091", "*"],
    web=True,
    # session_service_uri="sqlite:///memory.db",
)

# todo: logging endpoint
@app.get("/log")
async def log_message():
    return {"message": "Logging endpoint"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9091)

# launch browser > navigate to http://localhost:9091/docs
import pytest
import httpx
import uuid
from urllib.parse import urlparse

@pytest.fixture
def post_session_response():
    """Fixture to POST to /users/{user_id}/sessions/{session_id} with UUIDs."""
    user_id = f"u_{uuid.uuid4()}"
    session_id = f"s_{uuid.uuid4()}"
    url = f"http://localhost:9091/apps/queueflow_device_manager/users/{user_id}/sessions/{session_id}"
    json_data = {
        "state": {
            "key1": "value1",
            "key2": 42
        }
    }

    try:
        response = httpx.post(url, json=json_data)
        response.raise_for_status()
        # Return response and user/session info if needed
        return {
            "response": response,
            "user_id": user_id,
            "session_id": session_id
        }
    except httpx.HTTPStatusError as e:
        pytest.fail(f"Request to {url} failed with status code {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        pytest.fail(f"Request error while calling {e.request.url!r}: {e}")


def test_post_session(post_session_response):
    """Test POST to sessions endpoint."""
    response = post_session_response["response"]
    assert response.status_code == 200
    data = response.json()
    assert "state" in data

@pytest.mark.timeout(60)
def test_post_run(post_session_response):
    """Test POST to /run endpoint using user_id and session_id from post_session_response."""
    user_id = post_session_response["user_id"]
    session_id = post_session_response["session_id"]
    url = "http://localhost:9091/run"
    json_data = {
        "app_name": "queueflow_device_manager",
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [
                {
                    "text": "what tools do we have?"
                }
            ]
        }
    }

    try:
        response = httpx.post(url, json=json_data)
        response.raise_for_status()
        assert response.status_code == 200
        data = response.json()
        # Add assertions depending on expected response content
        # For example, check some keys in the returned data
    except httpx.HTTPStatusError as e:
        pytest.fail(f"Request to {url} failed with status code {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        pytest.fail(f"Request error while calling {e.request.url!r}: {e}")

@pytest.mark.timeout(60)
def test_post_run_sse(post_session_response):
    """Test POST to /run_sse endpoint using dynamic user_id and session_id with streaming enabled."""
    user_id = post_session_response["user_id"]
    session_id = post_session_response["session_id"]
    url = "http://localhost:9091/run_sse"
    json_data = {
        "app_name": "queueflow_device_manager",
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [
                {
                    "text": "what tool do we have?"
                }
            ]
        },
        "streaming": True
    }

    try:
        with httpx.Client() as client:
            # Use stream=True to get the raw streaming response
            with client.stream("POST", url, json=json_data) as response:
                response.raise_for_status()
                # Here you can read streamed chunks or lines as needed
                # e.g., print received lines or collect them
                received_messages = []
                for chunk in response.iter_text():
                    # You can customize parsing here, this just collects text chunks
                    if chunk.strip():
                        received_messages.append(chunk.strip())

        # Basic assertions after streaming completes
        assert received_messages, "No streaming messages received"
        # Optionally print or further inspect messages
        # print("Received streaming data:", received_messages)
    except httpx.HTTPStatusError as e:
        pytest.fail(f"Request to {url} failed with status code {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        pytest.fail(f"Request error while calling {e.request.url!r}: {e}")

"""Run the separate Moon relay service for local development."""

import uvicorn


if __name__ == "__main__":
    uvicorn.run("dera.relay.service:app", host="127.0.0.1", port=8787, reload=False)

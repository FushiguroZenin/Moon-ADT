"""Start Moon's local-only Dera1.4 HTTP API."""

import uvicorn


if __name__ == "__main__":
    uvicorn.run("dera.interface.api:app", host="127.0.0.1", port=8765, reload=False)

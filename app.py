"""ASGI entrypoint for local and Hugging Face Spaces Docker deployment."""
import os

from api.app import app


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("api.app:app", host="0.0.0.0", port=port)

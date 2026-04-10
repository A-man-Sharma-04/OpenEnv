"""ASGI entrypoint for local and Hugging Face Spaces Docker deployment."""
import os

from api.app import app


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("app:app", host=host, port=port)

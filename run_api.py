"""Start the SignalForge API server."""

from pathlib import Path

from dotenv import load_dotenv

# Load .env before any app imports that read settings
_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env", override=True)

import uvicorn

from app.config import get_settings, reload_settings

if __name__ == "__main__":
    reload_settings()
    s = get_settings()
    from app.brand import PRODUCT_NAME

    print(f"{PRODUCT_NAME} API → http://{s.api_host}:{s.api_port}")
    print(f"Agent configured: {s.agent_configured()}")
    uvicorn.run(
        "app.main:app",
        host=s.api_host,
        port=s.api_port,
        reload=False,
    )

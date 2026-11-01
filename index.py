"""Vercel entrypoint: Vercel loads the top-level `app` variable."""
from app import create_app

app = create_app()

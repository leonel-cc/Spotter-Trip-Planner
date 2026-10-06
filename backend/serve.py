"""Serve the built React application and Django API from one origin."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application
from waitress import serve

if __name__ == "__main__":
    serve(
        get_wsgi_application(),
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        threads=4,
        channel_timeout=180,
        trusted_proxy=os.getenv("TRUSTED_PROXY", "127.0.0.1"),
        trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto"},
    )

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

# Vercel imports this file from the repository root rather than the backend folder.
backend_directory = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_directory))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

"""Passenger entry point for the cPanel production application."""
import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

from config.wsgi import application as django_application  # noqa: E402


def application(environ, start_response):
    """Restore the public /api prefix stripped by a PassengerBaseURI mount."""
    script_name = environ.get("SCRIPT_NAME", "").rstrip("/")
    path_info = environ.get("PATH_INFO", "/")
    if script_name == "/api":
        environ["SCRIPT_NAME"] = ""
        if path_info != "/api" and not path_info.startswith("/api/"):
            environ["PATH_INFO"] = f"/api{path_info if path_info.startswith('/') else '/' + path_info}"
    return django_application(environ, start_response)

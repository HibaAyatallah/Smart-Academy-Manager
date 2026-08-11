#!/usr/bin/env python
"""Django command-line utility for administrative tasks."""
import os
import sys


def main() -> None:
    settings_module = (
        "config.settings.test"
        if len(sys.argv) > 1 and sys.argv[1] == "test"
        else "config.settings.local"
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    if len(sys.argv) > 1 and sys.argv[1] == "runserver" and len(sys.argv) == 2:
        sys.argv.append("0.0.0.0:8001")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Is it installed and available on your PYTHONPATH?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

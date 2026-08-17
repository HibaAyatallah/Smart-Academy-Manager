#!/bin/bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPANEL_HOME="${SMART_ACADEMY_CPANEL_HOME:-/home/capskill}"
APP_ROOT="${SMART_ACADEMY_APP_ROOT:-${CPANEL_HOME}/smart_academy_backend}"
PUBLIC_ROOT="${SMART_ACADEMY_PUBLIC_ROOT:-${CPANEL_HOME}/public_html}"
PYTHON_BIN="${SMART_ACADEMY_PYTHON:-}"

fail() { printf 'DEPLOY ERROR: %s\n' "$1" >&2; exit 1; }
step() { printf '\n==> %s\n' "$1"; }

command -v rsync >/dev/null 2>&1 || fail "rsync is required by the cPanel deployment."

if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in "${CPANEL_HOME}"/virtualenv/smart_academy_backend/*/bin/python; do
    if [[ -x "$candidate" ]]; then PYTHON_BIN="$candidate"; break; fi
  done
fi
[[ -n "$PYTHON_BIN" && -x "$PYTHON_BIN" ]] || fail "Set SMART_ACADEMY_PYTHON to the cPanel virtualenv Python executable."
[[ -f "${REPO_ROOT}/backend/manage.py" ]] || fail "backend/manage.py is missing."

step "Creating persistent directories"
mkdir -p "$APP_ROOT" "$APP_ROOT/media" "$APP_ROOT/staticfiles" "$APP_ROOT/logs" "$APP_ROOT/tmp" "$PUBLIC_ROOT"
chmod 750 "$APP_ROOT" "$APP_ROOT/logs" "$APP_ROOT/tmp"
chmod 755 "$APP_ROOT/media" "$APP_ROOT/staticfiles" "$PUBLIC_ROOT"

step "Synchronising backend code without persistent or secret files"
rsync -a --checksum \
  --exclude='.env' --exclude='.env.*' --exclude='.venv/' --exclude='venv/' \
  --exclude='media/' --exclude='staticfiles/' --exclude='logs/' --exclude='tmp/' \
  --exclude='__pycache__/' --exclude='*.py[cod]' --exclude='*.sqlite3' --exclude='*.log' \
  "$REPO_ROOT/backend/" "$APP_ROOT/"
[[ -f "$APP_ROOT/.env" ]] || fail "Create the production $APP_ROOT/.env securely before deploying."

step "Installing Python dependencies"
"$PYTHON_BIN" -m pip install --disable-pip-version-check -r "$APP_ROOT/requirements/base.txt"

export DJANGO_SETTINGS_MODULE=config.settings.production
step "Checking Django production configuration"
cd "$APP_ROOT"
"$PYTHON_BIN" manage.py check

step "Applying database migrations"
"$PYTHON_BIN" manage.py migrate --noinput

step "Collecting static files"
"$PYTHON_BIN" manage.py collectstatic --noinput

step "Locating or building the Angular production bundle"
ANGULAR_BROWSER="$REPO_ROOT/frontend/dist/smart-academy-manager-frontend/browser"
if [[ ! -f "$ANGULAR_BROWSER/index.html" ]]; then
  command -v npm >/dev/null 2>&1 || fail "Angular bundle is absent and npm is unavailable. Upload/build frontend/dist/smart-academy-manager-frontend/browser first."
  cd "$REPO_ROOT/frontend"
  npm ci
  npm run build -- --configuration=production
fi
[[ -f "$ANGULAR_BROWSER/index.html" ]] || fail "Angular production index.html is missing."

step "Publishing Angular without touching /api, /media or /static"
rsync -a --checksum --exclude='.htaccess' "$ANGULAR_BROWSER/" "$PUBLIC_ROOT/"

step "Exposing persistent static and media directories"
for name in static media; do
  if [[ "$name" == "static" ]]; then target="$APP_ROOT/staticfiles"; else target="$APP_ROOT/media"; fi
  link="$PUBLIC_ROOT/$name"
  if [[ -e "$link" && ! -L "$link" ]]; then
    fail "$link already exists and is not a symlink; move it manually before deployment."
  fi
  ln -sfn "$target" "$link"
done

step "Installing Apache/Passenger routing"
sed -e "s|@@APP_ROOT@@|$APP_ROOT|g" -e "s|@@PYTHON@@|$PYTHON_BIN|g" \
  "$REPO_ROOT/deploy/cpanel/public_html.htaccess" > "$PUBLIC_ROOT/.htaccess"

step "Restarting Passenger"
touch "$APP_ROOT/tmp/restart.txt"
printf '\nDeployment prepared successfully.\n'

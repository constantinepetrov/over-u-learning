#!/usr/bin/env bash
set -euo pipefail
if [ "$(id -u)" -eq 0 ]; then
  chown frappe:frappe /home/frappe/frappe-bench
  ln -sfn /home/frappe/frappe-bench/sites /sites
  exec /usr/sbin/runuser -u frappe -- /bin/bash /workspace/over-u/dev/init.sh
fi
if [ ! -f frappe-bench/sites/apps.txt ]; then
  bench init --ignore-exist --frappe-branch v16.51.0 --skip-redis-config-generation --skip-assets frappe-bench
fi
cd frappe-bench
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379
sed -i '/^redis/d; /^watch/d' Procfile
if [ ! -d apps/payments ]; then
  bench get-app https://github.com/frappe/payments --branch version-16 --skip-assets
  git -C apps/payments fetch origin cca07d9f9392e2ea0e521c5975151db9e4b6c321
  git -C apps/payments checkout --detach cca07d9f9392e2ea0e521c5975151db9e4b6c321
  uv pip install -e apps/payments --python env/bin/python
fi
if ! grep -qx lms sites/apps.txt; then
  if [ -L apps/lms ]; then unlink apps/lms; fi
  bench get-app /workspace --soft-link --skip-assets
fi
if [ ! -d apps/over_u ]; then ln -s /workspace/over-u/apps/over_u apps/over_u; fi
if ! grep -qx over_u sites/apps.txt; then
  uv pip install -e apps/over_u --python env/bin/python
  printf '\nover_u\n' >> sites/apps.txt
fi
if [ ! -f sites/over-u.localhost/site_config.json ]; then
  bench new-site over-u.localhost --mariadb-root-password "$OVER_U_DB_PASSWORD" --admin-password "$OVER_U_ADMIN_PASSWORD" --no-mariadb-socket
  bench --site over-u.localhost install-app payments
  bench --site over-u.localhost install-app lms
  bench --site over-u.localhost set-config developer_mode 1
  bench --site over-u.localhost set-config allow_tests true
  bench use over-u.localhost
fi
bench --site over-u.localhost install-app over_u
ln -sfn "$PWD/apps/frappe/ui" /workspace/frontend/node_modules/@framework/ui
if [ ! -f /workspace/lms/www/_lms.html ] || [ ! -f sites/assets/assets.json ]; then bench build; fi
bench --site over-u.localhost execute over_u.school.seed
exec bench start

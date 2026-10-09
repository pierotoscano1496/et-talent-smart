#!/usr/bin/env bash
set -euo pipefail
umask 077
repository="${1:?repository is required}"
release="${2:?commit is required}"
[[ "$repository" =~ ^[a-z0-9._-]+/[a-z0-9._-]+$ && "$release" =~ ^[a-f0-9]{40}$ ]] || exit 2
root="/opt/talentsmart"
cd "$root/releases/$release"
# An additional server lock covers manual executions outside Actions.
exec 9>"$root/deploy.lock"
flock -n 9 || { echo "Ya hay un despliegue en curso" >&2; exit 1; }
export BACKEND_IMAGE="ghcr.io/$repository-backend:$release"
export PAGINA_CONTROL_IMAGE="ghcr.io/$repository-pagina-control:$release"
export TALENTOSITO_IMAGE="ghcr.io/$repository-talentosito:$release"
export MINIO_IMAGE="ghcr.io/$repository-minio:$release"
export MINIO_MC_IMAGE="ghcr.io/$repository-minio-mc:$release"
dc() { docker compose --env-file /etc/talentsmart/qa.env -p talentsmart-qa -f compose.yaml -f compose.qa.yaml "$@"; }
dc config --quiet
# Validate the reserved port constraint without printing resolved secrets.
port=$(dc config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["gateway"]["ports"][0]["published"])')
case "$port" in 9082|4567|3307) echo "Puerto reservado por otro servicio" >&2; exit 1;; esac
for container in $(docker ps -q --filter "publish=$port"); do
  owner=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$container")
  [ "$owner" = "talentsmart-qa" ] || { echo "Puerto ocupado por otro contenedor" >&2; exit 1; }
done
gateway=$(docker ps -q --filter label=com.docker.compose.project=talentsmart-qa --filter label=com.docker.compose.service=gateway --filter "publish=$port")
if ss -H -ltn "sport = :$port" | grep -q . && [ -z "$gateway" ]; then
  echo "Puerto ocupado por otro proceso del host" >&2
  exit 1
fi
dc pull
dc run --rm --no-deps backend python manage.py check --deploy --fail-level ERROR
dc up -d --wait postgres minio
dc run --rm --no-deps minio-init
# Pause writers so the SQL and object backups refer to the same state.
dc stop gateway pagina-control backend talentosito
stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup="$root/backups/$stamp-$release"
mkdir -p "$backup"
dc exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup/database.dump"
dc run --rm -T --no-deps backend python manage.py backup_storage > "$backup/files.tar"
dc run --rm --no-deps backend python manage.py migrate --noinput
dc up -d --wait backend talentosito pagina-control gateway
# Persist image identities separately from secrets, for operator commands.
printf 'BACKEND_IMAGE=%s\nTALENTOSITO_IMAGE=%s\nMINIO_IMAGE=%s\nMINIO_MC_IMAGE=%s\nPAGINA_CONTROL_IMAGE=%s\n' \
  "$BACKEND_IMAGE" "$TALENTOSITO_IMAGE" "$MINIO_IMAGE" "$MINIO_MC_IMAGE" "$PAGINA_CONTROL_IMAGE" > release.env
ln -sfn "$root/releases/$release" "$root/current"
echo "QA actualizado: $release. Respaldo: $backup"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

case $(uname -m) in
  x86_64)   export DOCKER_HOST_ARCH=amd64 ;;
  aarch64|arm64) export DOCKER_HOST_ARCH=arm64 ;;
  *)        export DOCKER_HOST_ARCH=amd64 ;;
esac

export DOCKER_HOST_OS=$(uname -s | tr '[:upper:]' '[:lower:]')

export DOCKER_PLATFORM="${DOCKER_HOST_OS}/${DOCKER_HOST_ARCH}"

echo "DOCKER_PLATFORM: $DOCKER_PLATFORM"

STORAGE_BACKEND="s3"

args=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --storage)
      STORAGE_BACKEND="$2"
      shift 2
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

export COMPOSE_PROFILES="${STORAGE_BACKEND}"
export BLOB_BACKEND_TYPE="${STORAGE_BACKEND}"

echo $BLOB_BACKEND_TYPE

# Forward all arguments to docker compose; default to "up" when no args given
exec docker compose -f "$COMPOSE_FILE" "${args[@]:-up}"
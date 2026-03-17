#!/usr/bin/env bash
set -euo pipefail

# Build Docker images for application services (linux/amd64 + linux/arm64), tag with
# registry and one or more tags, then push. Uses docker buildx for multi-platform builds.
# Usage: ./scripts/build-push-prod-images.sh <registry> <tag> [tag ...] [prod|dev]
#   prod (default) - use Dockerfile.prod for production deployments
#   dev            - use Dockerfile.dev for dev deployments (must be last arg if used)
# Example: ./scripts/build-push-prod-images.sh ghcr.io/myorg 0.2.0 latest
# Example: ./scripts/build-push-prod-images.sh ghcr.io/myorg 0.2.0 latest prod
# Example: ./scripts/build-push-prod-images.sh ghcr.io/myorg latest dev
# Requires: docker buildx (multi-platform builder, e.g. docker buildx create --use)

REGISTRY="${1:?Usage: $0 <registry> <tag> [tag ...] [prod|dev]}"
shift
if [[ $# -eq 0 ]]; then
  echo "Error: at least one tag (or tag and mode) required."
  echo "Usage: $0 <registry> <tag> [tag ...] [prod|dev]"
  exit 1
fi

# If last arg is prod or dev, it's the mode; the rest are tags.
LAST="${*: -1}"
case "$LAST" in
  prod|dev) MODE="$LAST"; TAGS=("${@:1:$#-1}") ;;
  *)        MODE="prod";  TAGS=("$@") ;;
esac

if [[ ${#TAGS[@]} -eq 0 ]]; then
  echo "Error: at least one tag required."
  echo "Usage: $0 <registry> <tag> [tag ...] [prod|dev]"
  exit 1
fi

case "$MODE" in
  prod) DOCKERFILE_NAME="Dockerfile.prod" ;;
  dev)  DOCKERFILE_NAME="Dockerfile.dev" ;;
  *)
    echo "Error: mode must be 'prod' or 'dev', got: $MODE"
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXTRA="$REPO_ROOT/extra"

SERVICES=(
  "matyan-backend"
  "matyan-frontier"
  "matyan-ui"
)

# First tag is used as IMAGE_VERSION build-arg for OCI labels
IMAGE_VERSION="${TAGS[0]}"
echo "Building for $MODE (using $DOCKERFILE_NAME), tags: ${TAGS[*]}..."

pids=()
for service in "${SERVICES[@]}"; do
  (
    dockerfile="$EXTRA/$service/$DOCKERFILE_NAME"

    if [[ ! -f "$dockerfile" ]]; then
      echo "[$service] Skipping: $dockerfile not found"
      exit 0
    fi

    if [[ "$MODE" == "dev" ]]; then
      context="$EXTRA"
    else
      context="$EXTRA/$service"
    fi

    tag_args=()
    for t in "${TAGS[@]}"; do
      tag_args+=(-t "${REGISTRY}/${service}:${t}")
    done

    echo "[$service] Building for linux/amd64,linux/arm64 (context: $context)..."
    docker buildx build --platform linux/amd64,linux/arm64 \
      --build-arg "IMAGE_VERSION=${IMAGE_VERSION}" \
      -f "$dockerfile" \
      "${tag_args[@]}" \
      --push \
      "$context"
    echo "[$service] Done."
  ) &
  pids+=($!)
done

failed=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    ((failed++)) || true
  fi
done
if [[ $failed -gt 0 ]]; then
  echo "Error: $failed build(s) failed."
  exit 1
fi

echo "Done. Images pushed:"
for service in "${SERVICES[@]}"; do
  for t in "${TAGS[@]}"; do
    echo "  ${REGISTRY}/${service}:${t}"
  done
done

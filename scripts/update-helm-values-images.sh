#!/usr/bin/env bash
set -euo pipefail

# Update deploy/helm/matyan/values.yaml with the given image repository prefix and tag.
# All application images (backend, frontier, ui, ingestionWorker, controlWorker) are updated.
# Usage: ./scripts/update-helm-values-images.sh <repo> <tag>
# Example: ./scripts/update-helm-values-images.sh ghcr.io/myorg v1.2.0
# Example: ./scripts/update-helm-values-images.sh 288888 latest

REPO="${1:?Usage: $0 <repo> <tag>}"
TAG="${2:?Usage: $0 <repo> <tag>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALUES_FILE="$SCRIPT_DIR/../deploy/helm/matyan/values.yaml"

if [[ ! -f "$VALUES_FILE" ]]; then
  echo "Error: values file not found: $VALUES_FILE"
  exit 1
fi

# Escape for sed: / and & must be escaped in replacement
REPO_ESCAPED=$(printf '%s\n' "$REPO" | sed 's/[\/&]/\\&/g')
TAG_ESCAPED=$(printf '%s\n' "$TAG" | sed 's/[\/&]/\\&/g')

# Update repository and tag in one pass; keep one backup of the original file
sed -i.bak \
  -e "s|repository: .*/matyan-backend|repository: ${REPO_ESCAPED}/matyan-backend|g" \
  -e "s|repository: .*/matyan-frontier|repository: ${REPO_ESCAPED}/matyan-frontier|g" \
  -e "s|repository: .*/matyan-ui|repository: ${REPO_ESCAPED}/matyan-ui|g" \
  -e "/^backend:/,/^frontier:/ s/^    tag: .*/    tag: ${TAG_ESCAPED}/" \
  -e "/^frontier:/,/^ui:/ s/^    tag: .*/    tag: ${TAG_ESCAPED}/" \
  -e "/^ui:/,/^ingestionWorker:/ s/^    tag: .*/    tag: ${TAG_ESCAPED}/" \
  -e "/^ingestionWorker:/,/^controlWorker:/ s/^    tag: .*/    tag: ${TAG_ESCAPED}/" \
  -e "/^controlWorker:/,/^ingress:/ s/^    tag: .*/    tag: ${TAG_ESCAPED}/" \
  "$VALUES_FILE"

# Remove backup (optional: delete to keep original; keep .bak to restore)
rm -f "${VALUES_FILE}.bak"

echo "Updated $VALUES_FILE:"
echo "  repository prefix: $REPO"
echo "  tag: $TAG"
echo "  backend.image, frontier.image, ui.image, ingestionWorker.image, controlWorker.image"

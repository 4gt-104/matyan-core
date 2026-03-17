#!/usr/bin/env bash
# Build MkDocs and copy the static site into the gh-pages submodule so it can be
# pushed to https://github.com/4gt-104/4gt-104.github.io and served at
# https://4gt-104.github.io/matyan-core/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GH_PAGES="${REPO_ROOT}/gh-pages"
SITE_DIR="${REPO_ROOT}/site"
TARGET_DIR="${GH_PAGES}/matyan-core"

if [[ ! -e "${GH_PAGES}/.git" ]]; then
  echo "gh-pages submodule is not initialized. Run from repo root:"
  echo "  git submodule update --init gh-pages"
  echo ""
  echo "If the 4gt-104.github.io repo is empty, create an initial commit there first"
  echo "(e.g. add a README and push), then run the above again."
  exit 1
fi

cd "${REPO_ROOT}"
echo "Building documentation..."
uv run mkdocs build

echo "Copying site to gh-pages/matyan-core..."
rm -rf "${TARGET_DIR}"
mkdir -p "${TARGET_DIR}"
cp -a "${SITE_DIR}"/* "${TARGET_DIR}/"

echo "Done. To publish:"
echo "  cd gh-pages"
echo "  git add matyan-core"
echo "  git commit -m 'Update matyan-core documentation'"
echo "  git push"

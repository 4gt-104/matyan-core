#!/usr/bin/env bash
# Package the Matyan Helm chart (with subchart dependencies) and publish it to
# the gh-pages submodule under helm/ so it is available at
# https://4gt-104.github.io/matyan-core/helm for Kustomize/helm install.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHART_DIR="${REPO_ROOT}/deploy/helm/matyan"
GH_PAGES="${REPO_ROOT}/gh-pages"
HELM_REPO_URL="https://4gt-104.github.io/matyan-core/helm"
HELM_DIR="${GH_PAGES}/helm"

if [[ ! -e "${GH_PAGES}/.git" ]]; then
  echo "gh-pages submodule is not initialized. Run from repo root:"
  echo "  git submodule update --init gh-pages"
  exit 1
fi

if ! command -v helm &>/dev/null; then
  echo "helm is required. Install it from https://helm.sh/docs/intro/install/"
  exit 1
fi

# Use a cache inside the repo so we don't need write access to ~/.cache
export HELM_CACHE_HOME="${REPO_ROOT}/.helm/cache"
export HELM_REPO_CACHE="${REPO_ROOT}/.helm/repository"
mkdir -p "${HELM_CACHE_HOME}" "${HELM_REPO_CACHE}"

cd "${CHART_DIR}"
echo "Updating Helm chart dependencies (fetching and packaging subcharts)..."
helm dependency update

echo "Packaging matyan chart..."
helm package . --destination "${REPO_ROOT}"

mkdir -p "${HELM_DIR}"
# Move the built tgz into gh-pages/helm (helm package writes to destination with version in filename)
mv "${REPO_ROOT}"/matyan-*.tgz "${HELM_DIR}/"

cd "${HELM_DIR}"
if [[ -f index.yaml ]]; then
  echo "Merging into existing Helm repo index..."
  helm repo index . --url "${HELM_REPO_URL}" --merge index.yaml
else
  echo "Creating Helm repo index..."
  helm repo index . --url "${HELM_REPO_URL}"
fi

echo "Done. Helm chart published under gh-pages/helm/. To push:"
echo "  cd gh-pages"
echo "  git add helm"
echo "  git commit -m 'Add or update matyan Helm chart'"
echo "  git push"
echo ""
echo "Then use in Kustomize with:"
echo "  helmCharts:"
echo "    - name: matyan"
echo "      repo: ${HELM_REPO_URL}"
echo "      version: \"0.1.0\""
echo "      namespace: matyan"
echo "      releaseName: matyan"
echo "      valuesFile: values.yaml"

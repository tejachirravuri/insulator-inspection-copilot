#!/usr/bin/env bash
# Build the image locally, push it to the private Azure Container Registry, switch the app.
# Run from the repository root (Git Bash on Windows works):   bash infra/release.sh
#
# The YOLO weights in models/ are copied into the image, which only ever goes to the private
# registry. Azure CLI runs in a container, so it does not need to be installed.
set -euo pipefail

AZ_IMAGE=mcr.microsoft.com/azure-cli:latest
REPO_DIR="$(pwd -W 2>/dev/null || pwd)"   # Windows path for Docker volume mounts in Git Bash
az_step() {
  MSYS_NO_PATHCONV=1 docker run --rm -v azcli-home:/root/.azure -v "$REPO_DIR:/work" -w /work \
    "$AZ_IMAGE" sh infra/deploy.sh "$@"
}

TAG="$(date +%Y%m%d-%H%M%S)"
read -r SERVER TOKEN < <(az_step token)
IMAGE="$SERVER/inspection-copilot:$TAG"

echo "== build $IMAGE"
docker build -t "$IMAGE" .

echo "== push"
# ACR accepts this fixed user name together with an Azure AD access token.
echo "$TOKEN" | docker login "$SERVER" -u 00000000-0000-0000-0000-000000000000 --password-stdin
docker push "$IMAGE"

echo "== switch the app"
az_step switch "$IMAGE"

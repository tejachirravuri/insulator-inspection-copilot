#!/bin/sh
# Azure steps. Runs inside the Azure CLI container with the repository mounted at /work:
#
#   docker run --rm -v azcli-home:/root/.azure -v "<repo>:/work" -w /work \
#     mcr.microsoft.com/azure-cli:latest sh infra/deploy.sh <step> [image]
#
# Steps:
#   infra          create / update all resources (placeholder image on the first run)
#   token          print a short-lived registry login token (used by infra/release.sh)
#   switch IMAGE   point the container app at IMAGE (listening on port 8000)
#   url            print the app URL
#
# Reads secrets from .env.azure (git-ignored). Idempotent: re-running updates in place.
# Images are built locally and pushed (infra/release.sh), because ACR cloud builds
# ("ACR Tasks") are not permitted on Azure for Students subscriptions.
set -eu
STEP="${1:-infra}"
set -a; . ./.env.azure; set +a

deploy_infra() {  # $1 = image, $2 = container port
  az deployment group create -g "$RESOURCE_GROUP" -f infra/main.bicep -o none \
    -p location="$LOCATION" postgresLocation="${POSTGRES_LOCATION:-$LOCATION}" \
       postgresName="${POSTGRES_NAME:-}" image="$1" targetPort="$2" clientIp="$CLIENT_IP" \
       postgresPassword="$POSTGRES_PASSWORD" anthropicApiKey="$ANTHROPIC_API_KEY" \
       accessCode="$ACCESS_CODE"
}

output() { az deployment group show -g "$RESOURCE_GROUP" -n main --query "properties.outputs.$1.value" -o tsv; }

case "$STEP" in
  infra)
    az group create -n "$RESOURCE_GROUP" -l "$LOCATION" -o none
    deploy_infra mcr.microsoft.com/k8se/quickstart:latest 80
    echo "app URL: $(output appUrl)"
    ;;
  token)
    # stdout: "<login server> <token>"; the token is valid for about 3 hours
    echo "$(output registryLoginServer) $(az acr login -n "$(output registryName)" --expose-token --query accessToken -o tsv 2>/dev/null)"
    ;;
  switch)
    deploy_infra "$2" 8000
    echo "app URL: $(output appUrl)"
    ;;
  url)
    output appUrl
    ;;
  *)
    echo "unknown step: $STEP" >&2; exit 2
    ;;
esac

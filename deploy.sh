#!/bin/bash

# Use e.g. `direnv` to set the DIDDLE_ variables

set -euxo pipefail

IMAGE=${DIDDLE_OCI_REGISTRY}/diddle:latest

# Build
docker build --progress plain --platform linux/amd64 -t "$IMAGE" .
docker push "$IMAGE"

# Deploy
ssh "${DIDDLE_SSH_SERVER}" "${DIDDLE_UPDATE_COMMAND}"

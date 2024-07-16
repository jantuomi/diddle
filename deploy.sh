#!/bin/bash

set -euxo pipefail

IMAGE=registry.jan.systems/diddle:latest

# Build
docker build --progress plain --platform linux/amd64 -t "$IMAGE" .
docker push "$IMAGE"

# Deploy
ssh jan.systems 'cd deployments/diddle && bash dc-restart.sh'

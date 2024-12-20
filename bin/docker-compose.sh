#!/bin/sh
export DOCKER_DEFAULT_PLATFORM=linux/amd64
# Pass commands to Docker Compose v2 depending on what is present
docker compose $*

#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

exec bash Frontend_bot/deploy-logistic-vps.sh "$@"

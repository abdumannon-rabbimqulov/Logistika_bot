#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

exec bash deploy-all.sh "$@"

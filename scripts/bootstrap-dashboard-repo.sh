#!/usr/bin/env bash
# One-time seed of the dashboard repository from the committed site/ snapshot.
# Keeps the enrichment cursor and all fetched JSON so the first external-mode
# run continues the rotation seamlessly.
#
# Requires: gh CLI authenticated (gh auth login) and push rights to both repos.
# Usage:   ./scripts/bootstrap-dashboard-repo.sh
# Env:     DATA_REPO (default pekaboo/wuhan-housing-market-dashboard)
#          DATA_REPO_VISIBILITY (default public)
set -euo pipefail

DATA_REPO="${DATA_REPO:-pekaboo/wuhan-housing-market-dashboard}"
DATA_REPO_VISIBILITY="${DATA_REPO_VISIBILITY:-public}"

command -v gh >/dev/null 2>&1 || { echo "error: gh CLI is required (gh auth login)."; exit 1; }
[ -d site ] || { echo "error: run from the repository root; site/ is missing."; exit 1; }

remote="https://github.com/${DATA_REPO}.git"
if [ -n "$(git ls-remote "$remote" HEAD 2>/dev/null)" ]; then
  echo "error: refusing to seed, ${DATA_REPO} already has commits."
  exit 1
fi

gh repo view "$DATA_REPO" >/dev/null 2>&1 || gh repo create "$DATA_REPO" "--${DATA_REPO_VISIBILITY}"

gh auth setup-git >/dev/null

seed="$(mktemp -d)"
trap 'rm -rf "$seed"' EXIT
git archive HEAD:site | tar -x -C "$seed"
git -C "$seed" init --initial-branch=main >/dev/null
git -C "$seed" add -A
git -C "$seed" \
  -c user.name='pekaboo-task[bot]' \
  -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
  commit -m 'chore: seed dashboard repository from the task repository site snapshot' >/dev/null
git -C "$seed" push "$remote" main:main

echo "seeded ${DATA_REPO} from HEAD:site"

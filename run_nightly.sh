#!/bin/zsh
# Ramayan batch video generator — manual trigger, caffeinate mode.
# Prevents Mac from sleeping until the entire batch is done.
#
# Usage:
#   ./run_nightly.sh          # Generate 3 episodes (default)
#   ./run_nightly.sh 5        # Generate 5 episodes
#
# Just run it before bed. Mac stays awake until all episodes are done,
# then sleeps normally.

set -euo pipefail

# ─── Configuration ───────────────────────────────────────────
PROJECT_DIR="/Users/mukul.gaddhyan/Git/Personal-Youtube-Video-Genarator"
VENV_DIR="${PROJECT_DIR}/.venv"
EPISODE_COUNT="${1:-3}"
COOLDOWN_SECONDS=30

# ─── Environment Setup ───────────────────────────────────────
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

source "${VENV_DIR}/bin/activate"
cd "${PROJECT_DIR}"

# ─── Caffeinate + Run ────────────────────────────────────────
# -i: prevent idle sleep  -s: prevent system sleep (even on lid close with power)
# caffeinate wraps the batch process — dies automatically when batch exits
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ☕ Caffeinate ON — Mac will stay awake"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting batch: ${EPISODE_COUNT} episodes"
echo ""

caffeinate -is python generate_batch.py \
    --count "${EPISODE_COUNT}" \
    --delay "${COOLDOWN_SECONDS}"

EXIT_CODE=$?

echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Batch finished (exit code: ${EXIT_CODE})"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ☕ Caffeinate OFF — Mac can sleep now"

# ─── macOS notification ──────────────────────────────────────
if [ ${EXIT_CODE} -eq 0 ]; then
    osascript -e "display notification \"${EPISODE_COUNT} episodes generated successfully\" with title \"Ramayan Batch ✅\""
else
    osascript -e "display notification \"Batch finished with errors — check logs\" with title \"Ramayan Batch ⚠️\""
fi

exit ${EXIT_CODE}

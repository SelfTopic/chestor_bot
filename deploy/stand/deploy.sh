#!/usr/bin/env bash
# Тестовый стенд: раз в минуту (таймер systemd) ставит последнюю запушенную ветку, если CI
# на её коммите зелёный, и пишет в Telegram, что вышло. Настройки — /etc/chestor-stand.env.
set -euo pipefail

: "${STAND_DIR:?в /etc/chestor-stand.env нужен STAND_DIR — папка с клоном стенда}"
: "${NOTIFY_CHAT_ID:?в /etc/chestor-stand.env нужен NOTIFY_CHAT_ID — кому писать}"
REPO="${GITHUB_REPO:-SelfTopic/chestor_bot}"
PROJECT="${STAND_PROJECT:-chestor_test}"
SERVICES="${STAND_SERVICES:-bot}"

cd "$STAND_DIR"
# Сборка образа идёт дольше минуты: следующий запуск таймера не должен начать вторую.
exec 9>.stand.lock
flock -n 9 || exit 0

DEPLOYED=.stand_deployed
REJECTED=.stand_rejected

notify() {
    local token
    token=$(grep -m1 '^BOT_TOKEN=' .env | cut -d= -f2- | tr -d "\"'")
    curl -s -o /dev/null "https://api.telegram.org/bot${token}/sendMessage" \
        --data-urlencode "chat_id=${NOTIFY_CHAT_ID}" --data-urlencode "text=$1" || true
}

# success, failure или pending — по check runs коммита на GitHub.
ci_status() {
    local auth=()
    [[ -n "${GITHUB_TOKEN:-}" ]] && auth=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
    curl -sf "${auth[@]}" -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${REPO}/commits/$1/check-runs?per_page=100" |
        python3 -c '
import json, sys
runs = json.load(sys.stdin).get("check_runs", [])
if not runs or any(run["status"] != "completed" for run in runs):
    print("pending")
elif all(run["conclusion"] in ("success", "skipped", "neutral") for run in runs):
    print("success")
else:
    print("failure")
' || echo pending
}

git fetch --quiet --prune origin
branch=$(git for-each-ref --sort=-committerdate --format='%(refname:lstrip=3)' refs/remotes/origin |
    grep -vx HEAD | head -n1)
sha=$(git rev-parse "origin/${branch}")
short=${sha:0:7}

[[ "$sha" == "$(cat "$DEPLOYED" 2>/dev/null || true)" ]] && exit 0
[[ "$sha" == "$(cat "$REJECTED" 2>/dev/null || true)" ]] && exit 0

case "$(ci_status "$sha")" in
    pending) exit 0 ;;
    failure)
        echo "$sha" > "$REJECTED"
        notify "❌ CI красный: ${branch} (${short}) на стенд не ставлю. https://github.com/${REPO}/commit/${sha}"
        exit 0
        ;;
esac

subject=$(git log -1 --format=%s "$sha")
git checkout --quiet --force --detach "$sha"
# shellcheck disable=SC2086 — SERVICES — список сервисов через пробел.
if log=$(docker compose -p "$PROJECT" up -d --build --remove-orphans $SERVICES 2>&1); then
    echo "$sha" > "$DEPLOYED"
    notify "✅ На стенде ${branch} (${short}): ${subject}"
else
    echo "$sha" > "$REJECTED"
    notify "❌ Стенд не поднялся на ${branch} (${short}):
$(tail -n 20 <<< "$log")"
fi

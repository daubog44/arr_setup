#!/bin/sh
set -eu

. /bootstrap/semaphore-maintenance-catalog.sh

BASE="${SEMAPHORE_URL}"
USERNAME="${SEMAPHORE_ADMIN_USERNAME}"
PASS="${SEMAPHORE_ADMIN_PASSWORD}"
CURL_ARGS="-fsS --connect-timeout 10 --max-time 30"

echo "Waiting for Semaphore to be ready..."
until curl $CURL_ARGS "$BASE/api/ping" > /dev/null 2>&1; do
  echo "  Not ready yet, sleeping 5s..."
  sleep 5
done
echo "Semaphore is ready!"

curl $CURL_ARGS -c /tmp/cookies.txt -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"auth\":\"$USERNAME\",\"password\":\"$PASS\"}" > /dev/null
echo "Semaphore admin authentication succeeded."

api() {
  METHOD="$1"
  PATH_SUFFIX="$2"
  shift 2
  curl $CURL_ARGS -b /tmp/cookies.txt -X "$METHOD" "$BASE$PATH_SUFFIX" "$@"
}

api_json() {
  METHOD="$1"
  PATH_SUFFIX="$2"
  PAYLOAD="$3"
  api "$METHOD" "$PATH_SUFFIX" -H "Content-Type: application/json" -d "$PAYLOAD"
}

find_named_id() {
  RESPONSE="$1"
  RESOURCE_NAME="$2"
  (printf '%s' "$RESPONSE" | tr '{' '\n' | grep "\"name\":\"$RESOURCE_NAME\"" | sed 's/.*"id":\([0-9]*\).*/\1/' | head -n 1) || true
}

find_schedule_id_by_template() {
  RESPONSE="$1"
  TEMPLATE_ID="$2"
  (printf '%s' "$RESPONSE" | tr '{' '\n' | grep "\"template_id\":$TEMPLATE_ID" | sed 's/.*"id":\([0-9]*\).*/\1/' | head -n 1) || true
}

json_escape_file() {
  awk 'BEGIN { ORS = "" } { gsub(/\\/, "\\\\"); gsub(/"/, "\\\""); printf "%s\\n", $0 }' "$1"
}

upsert_schedule() {
  TEMPLATE_ID="$1"
  SCHEDULE_NAME="$2"
  CRON_FORMAT="$3"
  PAYLOAD="{\"project_id\":$PROJECT_ID,\"template_id\":$TEMPLATE_ID,\"name\":\"$SCHEDULE_NAME\",\"cron_format\":\"$CRON_FORMAT\",\"active\":true}"
  CURRENT=$(api GET "/api/project/$PROJECT_ID/schedules")
  CURRENT_ID=$(find_schedule_id_by_template "$CURRENT" "$TEMPLATE_ID")
  if [ -n "$CURRENT_ID" ]; then
    echo "Updating schedule $CURRENT_ID for template $TEMPLATE_ID"
    api_json PUT "/api/project/$PROJECT_ID/schedules/$CURRENT_ID" "{\"id\":$CURRENT_ID,\"project_id\":$PROJECT_ID,\"template_id\":$TEMPLATE_ID,\"name\":\"$SCHEDULE_NAME\",\"cron_format\":\"$CRON_FORMAT\",\"active\":true}" > /dev/null
  else
    echo "Creating schedule for template $TEMPLATE_ID"
    api_json POST "/api/project/$PROJECT_ID/schedules" "$PAYLOAD" > /dev/null
  fi
}

EXISTING=$(api GET "/api/projects")
PROJECT_ID=$(find_named_id "$EXISTING" "HaaC Maintenance")
if [ -n "$PROJECT_ID" ]; then
  echo "Reusing managed Semaphore project ID: $PROJECT_ID"
  api_json PUT "/api/project/$PROJECT_ID" "{\"id\":$PROJECT_ID,\"name\":\"HaaC Maintenance\",\"alert\":true,\"alert_chat\":\"\",\"max_parallel_tasks\":1,\"type\":\"\"}" > /dev/null
else
  PROJECT=$(api_json POST "/api/projects" '{"name":"HaaC Maintenance","alert":true,"alert_chat":"","max_parallel_tasks":1}')
  PROJECT_ID=$(echo "$PROJECT" | sed 's/.*"id":\([0-9]*\).*/\1/')
  echo "Created project ID: $PROJECT_ID"
fi

KEYS=$(api GET "/api/project/$PROJECT_ID/keys")
KEY_ID=$(find_named_id "$KEYS" "HaaC Maintenance SSH Key")
MAINTENANCE_PRIVATE_KEY=$(json_escape_file "$MAINTENANCE_SSH_KEY_PATH")
if [ -n "$KEY_ID" ]; then
  echo "Updating maintenance SSH key ID: $KEY_ID"
  api_json PUT "/api/project/$PROJECT_ID/keys/$KEY_ID" "{\"id\":$KEY_ID,\"name\":\"HaaC Maintenance SSH Key\",\"project_id\":$PROJECT_ID,\"type\":\"ssh\",\"ssh\":{\"login\":\"\",\"passphrase\":\"\",\"private_key\":\"$MAINTENANCE_PRIVATE_KEY\"}}" > /dev/null
else
  KEY=$(api_json POST "/api/project/$PROJECT_ID/keys" "{\"name\":\"HaaC Maintenance SSH Key\",\"project_id\":$PROJECT_ID,\"type\":\"ssh\",\"ssh\":{\"login\":\"\",\"passphrase\":\"\",\"private_key\":\"$MAINTENANCE_PRIVATE_KEY\"}}")
  KEY_ID=$(echo "$KEY" | sed 's/.*"id":\([0-9]*\).*/\1/')
  echo "Created maintenance SSH key ID: $KEY_ID"
  KEYS=$(api GET "/api/project/$PROJECT_ID/keys")
fi

if [ -f /etc/repo-ssh/repo_deploy_ed25519 ]; then
  REPO_KEY_ID=$(find_named_id "$KEYS" "HaaC Repo Deploy Key")
  REPO_PRIVATE_KEY=$(json_escape_file /etc/repo-ssh/repo_deploy_ed25519)
  if [ -n "$REPO_KEY_ID" ]; then
    echo "Updating repo deploy key ID: $REPO_KEY_ID"
    api_json PUT "/api/project/$PROJECT_ID/keys/$REPO_KEY_ID" "{\"id\":$REPO_KEY_ID,\"name\":\"HaaC Repo Deploy Key\",\"project_id\":$PROJECT_ID,\"type\":\"ssh\",\"ssh\":{\"login\":\"git\",\"passphrase\":\"\",\"private_key\":\"$REPO_PRIVATE_KEY\"}}" > /dev/null
  else
    REPO_KEY=$(api_json POST "/api/project/$PROJECT_ID/keys" "{\"name\":\"HaaC Repo Deploy Key\",\"project_id\":$PROJECT_ID,\"type\":\"ssh\",\"ssh\":{\"login\":\"git\",\"passphrase\":\"\",\"private_key\":\"$REPO_PRIVATE_KEY\"}}")
    REPO_KEY_ID=$(echo "$REPO_KEY" | sed 's/.*"id":\([0-9]*\).*/\1/')
    echo "Created repo deploy key ID: $REPO_KEY_ID"
  fi
else
  REPO_KEY_ID=$(printf '%s' "$KEYS" | tr '{' '\n' | grep '"name":"None"' | sed 's/.*"id":\([0-9]*\).*/\1/' | head -n 1)
fi

REPOS=$(api GET "/api/project/$PROJECT_ID/repositories")
REPO_ID=$(find_named_id "$REPOS" "arr_setup")
if [ -n "$REPO_ID" ]; then
  echo "Updating repository ID: $REPO_ID"
  api_json PUT "/api/project/$PROJECT_ID/repositories/$REPO_ID" "{\"id\":$REPO_ID,\"name\":\"arr_setup\",\"project_id\":$PROJECT_ID,\"git_url\":\"$REPO_URL\",\"git_branch\":\"$REPO_REVISION\",\"ssh_key_id\":$REPO_KEY_ID}" > /dev/null
else
  REPO=$(api_json POST "/api/project/$PROJECT_ID/repositories" "{\"name\":\"arr_setup\",\"project_id\":$PROJECT_ID,\"git_url\":\"$REPO_URL\",\"git_branch\":\"$REPO_REVISION\",\"ssh_key_id\":$REPO_KEY_ID}")
  REPO_ID=$(echo "$REPO" | sed 's/.*"id":\([0-9]*\).*/\1/')
  echo "Created repository ID: $REPO_ID"
fi

INVENTORIES=$(api GET "/api/project/$PROJECT_ID/inventory")
INV_ID=$(find_named_id "$INVENTORIES" "HaaC Nodes")
if [ -n "$INV_ID" ]; then
  echo "Updating inventory ID: $INV_ID"
  api_json PUT "/api/project/$PROJECT_ID/inventory/$INV_ID" "{\"id\":$INV_ID,\"name\":\"HaaC Nodes\",\"project_id\":$PROJECT_ID,\"inventory\":\"$MAINTENANCE_INVENTORY_PATH\",\"type\":\"file\",\"ssh_key_id\":$KEY_ID,\"repository_id\":$REPO_ID,\"become_key_id\":null}" > /dev/null
else
  INV=$(api_json POST "/api/project/$PROJECT_ID/inventory" "{\"name\":\"HaaC Nodes\",\"project_id\":$PROJECT_ID,\"inventory\":\"$MAINTENANCE_INVENTORY_PATH\",\"type\":\"file\",\"ssh_key_id\":$KEY_ID,\"repository_id\":$REPO_ID,\"become_key_id\":null}")
  INV_ID=$(echo "$INV" | sed 's/.*"id":\([0-9]*\).*/\1/')
  echo "Created inventory ID: $INV_ID"
fi

ENVIRONMENTS=$(api GET "/api/project/$PROJECT_ID/environment")
ENV_ID=$(find_named_id "$ENVIRONMENTS" "Default")
DEFAULT_ENV="{\\\"ANSIBLE_HOST_KEY_CHECKING\\\":\\\"True\\\",\\\"HAAC_SSH_HOST_KEY_CHECKING\\\":\\\"accept-new\\\",\\\"HAAC_MAINTENANCE_SSH_PRIVATE_KEY_PATH\\\":\\\"$MAINTENANCE_SSH_KEY_PATH\\\",\\\"HAAC_SSH_KNOWN_HOSTS_PATH\\\":\\\"$MAINTENANCE_KNOWN_HOSTS_PATH\\\",\\\"DEBIAN_FRONTEND\\\":\\\"noninteractive\\\"}"
if [ -n "$ENV_ID" ]; then
  echo "Updating environment ID: $ENV_ID"
  api_json PUT "/api/project/$PROJECT_ID/environment/$ENV_ID" "{\"id\":$ENV_ID,\"name\":\"Default\",\"project_id\":$PROJECT_ID,\"env\":\"$DEFAULT_ENV\",\"json\":\"{}\"}" > /dev/null
else
  ENV=$(api_json POST "/api/project/$PROJECT_ID/environment" "{\"name\":\"Default\",\"project_id\":$PROJECT_ID,\"env\":\"$DEFAULT_ENV\",\"json\":\"{}\"}")
  ENV_ID=$(echo "$ENV" | sed 's/.*"id":\([0-9]*\).*/\1/')
  echo "Created environment ID: $ENV_ID"
fi

upsert_template() {
  TEMPLATE_NAME="$1"
  PLAYBOOK_PATH="$2"
  DESCRIPTION="$3"
  TEMPLATES=$(api GET "/api/project/$PROJECT_ID/templates")
  TEMPLATE_ID=$(find_named_id "$TEMPLATES" "$TEMPLATE_NAME")
  if [ -n "$TEMPLATE_ID" ]; then
    echo "Updating template '$TEMPLATE_NAME' ($TEMPLATE_ID)" >&2
    api_json PUT "/api/project/$PROJECT_ID/templates/$TEMPLATE_ID" "{\"id\":$TEMPLATE_ID,\"name\":\"$TEMPLATE_NAME\",\"project_id\":$PROJECT_ID,\"app\":\"ansible\",\"playbook\":\"$PLAYBOOK_PATH\",\"inventory_id\":$INV_ID,\"repository_id\":$REPO_ID,\"environment_id\":$ENV_ID,\"description\":\"$DESCRIPTION\"}" > /dev/null
  else
    TEMPLATE=$(api_json POST "/api/project/$PROJECT_ID/templates" "{\"name\":\"$TEMPLATE_NAME\",\"project_id\":$PROJECT_ID,\"app\":\"ansible\",\"playbook\":\"$PLAYBOOK_PATH\",\"inventory_id\":$INV_ID,\"repository_id\":$REPO_ID,\"environment_id\":$ENV_ID,\"description\":\"$DESCRIPTION\"}")
    TEMPLATE_ID=$(echo "$TEMPLATE" | sed 's/.*"id":\([0-9]*\).*/\1/')
    echo "Created template '$TEMPLATE_NAME' ($TEMPLATE_ID)" >&2
  fi
  printf '%s' "$TEMPLATE_ID"
}

ensure_smoke_execution() {
  TEMPLATE_ID="$1"
  TASKS=$(api GET "/api/project/$PROJECT_ID/tasks" || echo "[]")
  COMPACT_TASKS=$(printf '%s' "$TASKS" | tr -d '\n\r\t ')
  SUCCESS_COUNT=$(printf '%s' "$COMPACT_TASKS" | grep -o "\"template_id\":$TEMPLATE_ID[^}]*\"status\":\"success\"" | wc -l | tr -d ' ' || true)
  if [ "${SUCCESS_COUNT:-0}" -gt 0 ]; then
    echo "Semaphore smoke execution already succeeded"
    return 0
  fi
  echo "Launching Semaphore smoke execution for template $TEMPLATE_ID"
  TASK=$(api_json POST "/api/project/$PROJECT_ID/tasks" "{\"template_id\":$TEMPLATE_ID}")
  TASK_ID=$(echo "$TASK" | sed 's/.*"id":\([0-9]*\).*/\1/')
  if [ -z "$TASK_ID" ] || [ "$TASK_ID" = "$TASK" ]; then
    echo "Could not parse Semaphore smoke task ID from API response" >&2
    exit 1
  fi
  for _ in $(seq 1 36); do
    CURRENT=$(api GET "/api/project/$PROJECT_ID/tasks/$TASK_ID" || echo "{}")
    STATUS=$(printf '%s' "$CURRENT" | tr -d '\n\r\t ' | sed 's/.*"status":"\([^"]*\)".*/\1/')
    case "$STATUS" in
      success)
        echo "Semaphore smoke execution succeeded: task $TASK_ID"
        return 0
        ;;
      error|failed|stopped)
        echo "Semaphore smoke execution failed with status $STATUS: task $TASK_ID" >&2
        exit 1
        ;;
    esac
    sleep 5
  done
  echo "Timed out waiting for Semaphore smoke execution task $TASK_ID" >&2
  exit 1
}

TPL_K3S_ID=$(upsert_template "$MAINTENANCE_K3S_TEMPLATE_NAME" "$MAINTENANCE_K3S_PLAYBOOK_PATH" "$MAINTENANCE_K3S_TEMPLATE_DESCRIPTION")
echo "Reconciled K3s template ID: $TPL_K3S_ID"

TPL_PVE_ID=$(upsert_template "$MAINTENANCE_PROXMOX_TEMPLATE_NAME" "$MAINTENANCE_PROXMOX_PLAYBOOK_PATH" "$MAINTENANCE_PROXMOX_TEMPLATE_DESCRIPTION")
echo "Reconciled Proxmox template ID: $TPL_PVE_ID"

TPL_RESTORE_ID=$(upsert_template "$MAINTENANCE_RESTORE_TEMPLATE_NAME" "$MAINTENANCE_RESTORE_PLAYBOOK_PATH" "$MAINTENANCE_RESTORE_TEMPLATE_DESCRIPTION")
echo "Reconciled Restore DB template ID: $TPL_RESTORE_ID"

TPL_SMOKE_ID=$(upsert_template "$MAINTENANCE_SMOKE_TEMPLATE_NAME" "$MAINTENANCE_SMOKE_PLAYBOOK_PATH" "$MAINTENANCE_SMOKE_TEMPLATE_DESCRIPTION")
echo "Reconciled Smoke template ID: $TPL_SMOKE_ID"

upsert_schedule "$TPL_K3S_ID" "$MAINTENANCE_K3S_SCHEDULE_NAME" "$MAINTENANCE_K3S_SCHEDULE_CRON"
echo "Reconciled K3s schedule"

upsert_schedule "$TPL_PVE_ID" "$MAINTENANCE_PROXMOX_SCHEDULE_NAME" "$MAINTENANCE_PROXMOX_SCHEDULE_CRON"
echo "Reconciled Proxmox schedule (30min after K3s)"

ensure_smoke_execution "$TPL_SMOKE_ID"
echo "Reconciled Semaphore smoke history"

echo "Semaphore bootstrap complete."

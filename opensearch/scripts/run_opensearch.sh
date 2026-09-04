#!/usr/bin/env bash
#
# Start, stop and inspect the local OpenSearch node prepared by
# setup_opensearch.sh. Nothing is installed system-wide: the process runs from
# build/, writes its PID to build/opensearch.pid and its output to
# build/logs/. There is no service, no systemd unit and nothing to clean up
# besides deleting build/.
#
# `start` does not return until the cluster answers _cluster/health, so a script
# can chain straight into indexing instead of sleeping and hoping.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
BUILD="$ROOT/build"
PID_FILE="$BUILD/opensearch.pid"
STARTUP_LOG="$BUILD/logs/startup.log"
WAIT_SECONDS=180

usage() {
    cat <<'EOF'
Usage: scripts/run_opensearch.sh {start|stop|status|logs} [options]

Commands:
  start     start the node in the background and wait for the cluster to answer
  stop      stop the node
  status    report whether it runs, and what the cluster says about itself
  logs      tail the startup log

Options:
  --timeout SECONDS   how long start waits for the cluster (default: 180)
  -h, --help          show this help

Example:
  ./scripts/setup_opensearch.sh --host localhost
  ./scripts/run_opensearch.sh start
  ./scripts/run_opensearch.sh status
  ./scripts/run_opensearch.sh stop
EOF
}

log() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

COMMAND="${1:-}"
[ $# -gt 0 ] && shift || true
case "$COMMAND" in
    -h|--help|"") usage; [ -z "$COMMAND" ] && exit 1 || exit 0 ;;
esac

while [ $# -gt 0 ]; do
    case "$1" in
        --timeout) WAIT_SECONDS="${2:?--timeout needs a value}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown option: $1 (try --help)" ;;
    esac
done

[ -f "$BUILD/cluster.env" ] || die "build/cluster.env not found - run scripts/setup_opensearch.sh first"
# shellcheck disable=SC1091
. "$BUILD/cluster.env"

BASE_URL="$CLUSTER_SCHEME://$CLUSTER_HOST:$CLUSTER_PORT"
CURL_OPTS=(--silent --show-error --max-time 5)
if [ "$CLUSTER_MODE" != "insecure" ]; then
    CURL_OPTS+=(--cacert "$BUILD/tls/root-ca.pem" -u "admin:${OPENSEARCH_PASSWORD:-DevSummit#2026os}")
fi

running_pid() {
    [ -f "$PID_FILE" ] || return 1
    local pid
    pid="$(cat "$PID_FILE")"
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null || return 1
    printf '%s' "$pid"
}

case "$COMMAND" in
    start)
        if pid="$(running_pid)"; then
            log "already running (pid $pid) at $BASE_URL"
            exit 0
        fi
        [ -x "$OPENSEARCH_HOME/bin/opensearch" ] || die "$OPENSEARCH_HOME/bin/opensearch missing - re-run setup"
        mkdir -p "$BUILD/logs"
        log "starting OpenSearch $OPENSEARCH_VERSION ($CLUSTER_MODE mode) ..."
        # The bundled JDK, named explicitly: whatever JAVA_HOME happens to point
        # at on the machine is not what this node was tested against.
        OPENSEARCH_JAVA_HOME="$OPENSEARCH_HOME/jdk" \
        OPENSEARCH_PATH_CONF="$OPENSEARCH_HOME/config" \
            nohup "$OPENSEARCH_HOME/bin/opensearch" >"$STARTUP_LOG" 2>&1 &
        echo $! > "$PID_FILE"
        log "pid $(cat "$PID_FILE"), log build/logs/startup.log"

        printf 'waiting for %s ' "$BASE_URL"
        for _ in $(seq 1 "$WAIT_SECONDS"); do
            if health="$(curl "${CURL_OPTS[@]}" "$BASE_URL/_cluster/health" 2>/dev/null)"; then
                case "$health" in
                    *'"status"'*)
                        printf '\n'
                        log "cluster is up: $health"
                        log ""
                        log "next: python3 scripts/index_stations.py --recreate --host $BASE_URL \\"
                        if [ "$CLUSTER_MODE" = "insecure" ]; then
                            log "          --no-auth"
                        else
                            log "          --ca-cert build/tls/root-ca.pem"
                        fi
                        exit 0
                        ;;
                esac
            fi
            if ! running_pid >/dev/null; then
                printf '\n'
                log "the process exited during startup. Last lines of build/logs/startup.log:"
                tail -n 25 "$STARTUP_LOG" || true
                exit 1
            fi
            printf '.'
            sleep 1
        done
        printf '\n'
        die "cluster did not answer within ${WAIT_SECONDS}s - see build/logs/startup.log"
        ;;

    stop)
        if ! pid="$(running_pid)"; then
            log "not running"
            rm -f "$PID_FILE"
            exit 0
        fi
        log "stopping pid $pid ..."
        kill "$pid"
        for _ in $(seq 1 60); do
            running_pid >/dev/null || break
            sleep 1
        done
        if running_pid >/dev/null; then
            log "still alive after 60s, sending SIGKILL"
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
        log "stopped"
        ;;

    status)
        if pid="$(running_pid)"; then
            log "running, pid $pid"
        else
            log "not running"
        fi
        log "mode    : $CLUSTER_MODE"
        log "endpoint: $BASE_URL"
        if [ "$CLUSTER_MODE" != "insecure" ]; then
            log "CA cert : build/tls/root-ca.pem"
        fi
        if out="$(curl "${CURL_OPTS[@]}" "$BASE_URL/_cluster/health?pretty" 2>&1)"; then
            log "health  :"
            printf '%s\n' "$out" | sed 's/^/  /'
        else
            log "health  : no answer ($out)"
        fi
        ;;

    logs)
        [ -f "$STARTUP_LOG" ] || die "no startup log yet: $STARTUP_LOG"
        tail -n 60 "$STARTUP_LOG"
        ;;

    *)
        die "unknown command: $COMMAND (try --help)"
        ;;
esac

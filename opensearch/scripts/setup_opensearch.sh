#!/usr/bin/env bash
#
# Download and configure a local, single-node OpenSearch for ArcGIS testing.
#
# No Docker, no package manager, no root: the archive is unpacked into build/
# and everything - data, logs, TLS material, PID file - stays inside this use
# case. Deleting build/ undoes the whole thing.
#
# Two things are deliberately not flexible:
#
#   * The version comes from input/opensearch_dist.json and is 2.12.0, because
#     ArcGIS Pro 3.7 and ArcGIS Enterprise 12.1 certify exactly OpenSearch 2.12.
#     Tracking "latest" here would be tracking away from the only version the
#     client supports.
#   * The checksum is the one OpenSearch publishes next to the archive. A
#     mismatch aborts; it is never a warning.
#
# TLS is on by default because ArcGIS supports basic authentication only, and
# basic auth over plain HTTP is not something to put in a repository as the
# happy path. --insecure exists for quick curl work and turns the security
# plugin off entirely; since OpenSearch 2.12, leaving security on while turning
# HTTP TLS off is a broken configuration upstream, so there is no middle option.
#
# The HTTPS certificate is generated here rather than taken from OpenSearch's
# demo configuration, and that is not paranoia. The demo root CA shipped with
# 2.12.0 was issued on 2023-08-29 with a **30-day** validity and expired on
# 2023-09-28; the node certificate it signed runs to 2033. So the certified
# release hands you a chain that cannot validate, and every client rejects it
# with "certificate has expired" while the cluster itself starts happily. On top
# of that the demo certificate only covers `localhost`, `127.0.0.1` and
# `node-0.example.com`, so it could never serve a VM addressed by hostname.
# `--demo-certs` keeps the broken configuration, for demonstrating the failure.
#
# Certificates are made with the `keytool` of OpenSearch's own bundled JDK, so
# this works identically on Linux and Windows with nothing else installed.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
MANIFEST="$ROOT/input/opensearch_dist.json"
BUILD="$ROOT/build"

HOST="localhost"
MODE="secure"
ALLOW_MMAP="true"
FORCE="false"
OWN_CERTS="true"
EXTRA_SAN=""
# No "!" in this password on purpose: setup_opensearch.bat runs under
# `setlocal EnableDelayedExpansion`, where cmd silently eats an unmatched "!"
# out of any `set "VAR=..."`. The Windows node then carried a password one
# character shorter than the documented one and every client got a 401.
PASSWORD="${OPENSEARCH_INITIAL_ADMIN_PASSWORD:-DevSummit#2026os}"
# Protects the generated PKCS#12 keystore inside build/, which is gitignored.
KEYSTORE_PASSWORD="devsummit"

usage() {
    cat <<'EOF'
Usage: scripts/setup_opensearch.sh [options]

Download OpenSearch 2.12.0 into build/ and configure it as a single node.

Options:
  --host HOST      address OpenSearch binds to and that the TLS certificate has
                   to match. Use the VM's hostname or IP if ArcGIS Pro runs on
                   another machine (default: localhost)
  --insecure       disable the security plugin: plain HTTP on port 9200, no
                   credentials. Convenient for curl, and not the configuration
                   ArcGIS is documented against - it needs basic auth
  --no-mmap        set node.store.allow_mmap: false, so the node starts without
                   raising vm.max_map_count (which needs root)
  --san NAME       extra subject alternative name for the HTTPS certificate.
                   Repeatable. Prefix with 'ip:' for an address, otherwise it is
                   taken as a DNS name
  --demo-certs     keep OpenSearch's own demo certificates instead of generating
                   one. Their root CA expired on 2023-09-28, so every client
                   will reject the connection - this exists to show that, not to
                   work around it
  --password PW    admin password. Must survive OpenSearch's strength check -
                   'admin' does not, which is why there is a demo password
                   instead of admin/admin (default: the committed demo password,
                   or $OPENSEARCH_INITIAL_ADMIN_PASSWORD)
  --force          re-extract and re-configure even if build/ already has an
                   installation. Wipes its data directory
  -h, --help       show this help

Example:
  ./scripts/setup_opensearch.sh --host localhost
  ./scripts/run_opensearch.sh start

Requires: bash, curl (or wget), tar, sha512sum, python3.
EOF
}

log() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --host) HOST="${2:?--host needs a value}"; shift 2 ;;
        --insecure) MODE="insecure"; shift ;;
        --no-mmap) ALLOW_MMAP="false"; shift ;;
        --san) EXTRA_SAN="$EXTRA_SAN,${2:?--san needs a value}"; shift 2 ;;
        --demo-certs) OWN_CERTS="false"; shift ;;
        --password) PASSWORD="${2:?--password needs a value}"; shift 2 ;;
        --force) FORCE="true"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown option: $1 (try --help)" ;;
    esac
done

command -v python3 >/dev/null 2>&1 || die "python3 is required (it reads the manifest)"
command -v tar >/dev/null 2>&1 || die "tar is required"
[ -f "$MANIFEST" ] || die "manifest not found: $MANIFEST"

# -- which distribution --------------------------------------------------------

case "$(uname -m)" in
    x86_64|amd64) PLATFORM="linux-x64" ;;
    aarch64|arm64) PLATFORM="linux-arm64" ;;
    *) die "unsupported architecture: $(uname -m)" ;;
esac

read -r VERSION FILE URL BYTES SHA512 <<EOF
$(python3 - "$MANIFEST" "$PLATFORM" <<'PY'
import json, sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
dist = manifest["distributions"][sys.argv[2]]
print(manifest["version"], dist["file"], dist["url"], dist["bytes"], dist["sha512"])
PY
)
EOF

OS_HOME="$BUILD/opensearch-$VERSION"
ARCHIVE="$BUILD/dist/$FILE"

log "OpenSearch $VERSION ($PLATFORM), pinned by input/opensearch_dist.json"
log "  ArcGIS Pro 3.7 / Enterprise 12.1 certify exactly this release line"

# -- pre-flight: vm.max_map_count ---------------------------------------------

if [ "$ALLOW_MMAP" = "true" ] && [ -r /proc/sys/vm/max_map_count ]; then
    CURRENT_MAX_MAP="$(cat /proc/sys/vm/max_map_count)"
    if [ "$CURRENT_MAX_MAP" -lt 262144 ]; then
        log ""
        log "warning: vm.max_map_count is $CURRENT_MAX_MAP, OpenSearch wants 262144."
        log "         Either raise it (needs root):"
        log "             sudo sysctl -w vm.max_map_count=262144"
        log "         or re-run this script with --no-mmap, which configures the"
        log "         node to do without memory mapping. Fine for 449 documents."
        log ""
    fi
fi

# -- download ------------------------------------------------------------------

mkdir -p "$BUILD/dist"

verify_archive() {
    [ -f "$ARCHIVE" ] || return 1
    local actual
    actual="$(sha512sum "$ARCHIVE" | awk '{print $1}')"
    [ "$actual" = "$SHA512" ]
}

if verify_archive; then
    log "archive already present and checksum matches: build/dist/$FILE"
else
    if [ -f "$ARCHIVE" ]; then
        log "archive present but checksum does not match - downloading again"
        rm -f "$ARCHIVE"
    fi
    log "downloading $FILE ($((BYTES / 1024 / 1024)) MB) ..."
    if command -v curl >/dev/null 2>&1; then
        curl -fL --progress-bar -o "$ARCHIVE.part" "$URL"
    elif command -v wget >/dev/null 2>&1; then
        wget -q --show-progress -O "$ARCHIVE.part" "$URL"
    else
        die "neither curl nor wget available"
    fi
    mv "$ARCHIVE.part" "$ARCHIVE"
    command -v sha512sum >/dev/null 2>&1 || die "sha512sum is required"
    ACTUAL="$(sha512sum "$ARCHIVE" | awk '{print $1}')"
    if [ "$ACTUAL" != "$SHA512" ]; then
        rm -f "$ARCHIVE"
        die "checksum mismatch for $FILE
  expected $SHA512
  actual   $ACTUAL
The download was corrupt or the artifact changed. Nothing was installed."
    fi
    log "checksum verified (sha512, as published by OpenSearch)"
fi

# -- extract -------------------------------------------------------------------

if [ -d "$OS_HOME" ] && [ "$FORCE" != "true" ]; then
    log "installation already present: build/opensearch-$VERSION (use --force to redo)"
else
    [ -d "$OS_HOME" ] && { log "removing previous installation"; rm -rf "$OS_HOME"; }
    # The admin password lives in the .opendistro_security index, which is
    # initialised exactly once - on the first start against an empty data
    # directory. Keeping build/data across a re-setup therefore keeps the old
    # password no matter what internal_users.yml says, and the only symptom is
    # a 401. So --force wipes the data too, as the help text promises.
    [ -d "$BUILD/data" ] && { log "wiping the data directory (the security index holds the old password)"; rm -rf "$BUILD/data"; }
    log "extracting into build/ ..."
    tar -xzf "$ARCHIVE" -C "$BUILD"
    [ -d "$OS_HOME" ] || die "archive did not contain opensearch-$VERSION/"
fi

mkdir -p "$BUILD/data" "$BUILD/logs" "$BUILD/tls"

# Same trap from the other side: an installation that is already there is not
# re-extracted, so internal_users.yml still carries the hash of the first run
# and the security index carries the password of the first start. Say so
# instead of letting a changed --password fail silently later.
if [ "$MODE" != "insecure" ] && [ "$FORCE" != "true" ] && [ -d "$BUILD/data/nodes" ]; then
    log "note: build/data already holds an initialised cluster. Its admin password"
    log "      is the one from the first start and cannot be changed here - re-run"
    log "      with --force to wipe the data directory and set a new one."
fi

# -- configure -----------------------------------------------------------------

CONFIG="$OS_HOME/config/opensearch.yml"

cat > "$CONFIG" <<EOF
# Written by scripts/setup_opensearch.sh - do not edit by hand, re-run the
# script instead. A single throwaway node for local ArcGIS testing.
cluster.name: devsummit
node.name: devsummit-node-1
discovery.type: single-node

network.host: $HOST
http.port: 9200

path.data: $BUILD/data
path.logs: $BUILD/logs

# 449 documents do not need memory mapping, and setting this to false is the
# only way to start without root when vm.max_map_count is too low.
node.store.allow_mmap: $ALLOW_MMAP
EOF

if [ "$MODE" = "insecure" ]; then
    cat >> "$CONFIG" <<'EOF'

# --insecure: the security plugin is off. Plain HTTP, no authentication, no
# TLS. Since OpenSearch 2.12 the alternative - keeping security on and turning
# only HTTP TLS off - is an unsupported configuration upstream, so this is all
# or nothing. ArcGIS is documented against basic authentication, so this mode
# is for curl and debugging, not for the ArcGIS connection.
plugins.security.disabled: true
EOF
    log "configured WITHOUT the security plugin: http://$HOST:9200, no credentials"
else
    DEMO="$OS_HOME/plugins/opensearch-security/tools/install_demo_configuration.sh"
    [ -f "$DEMO" ] || die "security demo installer not found at $DEMO"

    log "installing demo TLS certificates and the admin user ..."
    # -y: assume yes, -i: initialise (write certificates and security settings
    # into opensearch.yml), -s: skip the update if opensearch.yml already
    # carries a plugins.security setting - the installer exits 0 in that case,
    # which is why this script always rewrites opensearch.yml first.
    OPENSEARCH_INITIAL_ADMIN_PASSWORD="$PASSWORD" \
        bash "$DEMO" -y -i -s \
        || die "the demo security installer failed. The most common cause is a
password that does not pass the strength check - 'admin' does not. Pass a
stronger one with --password."

    for pem in root-ca.pem esnode.pem esnode-key.pem; do
        [ -f "$OS_HOME/config/$pem" ] || die "expected $pem in config/ after setup"
    done

    if [ "$OWN_CERTS" = "true" ]; then
        KEYTOOL="$OS_HOME/jdk/bin/keytool"
        [ -x "$KEYTOOL" ] || die "keytool not found in the bundled JDK: $KEYTOOL"

        # localhost and the loopback addresses are always in, so a cluster bound
        # to a hostname is still reachable from the machine it runs on.
        SAN="dns:localhost,ip:127.0.0.1,ip:::1"
        case "$HOST" in
            localhost|127.0.0.1|::1|0.0.0.0) : ;;
            *[0-9].[0-9]*) SAN="$SAN,ip:$HOST" ;;
            *) SAN="$SAN,dns:$HOST" ;;
        esac
        SAN="$SAN$EXTRA_SAN"

        log "generating a CA and an HTTPS certificate for $HOST (SAN: $SAN) ..."
        log "  reason: the demo root CA of OpenSearch 2.12.0 expired on 2023-09-28"

        CA_STORE="$BUILD/tls/ca.p12"
        HTTP_STORE="$OS_HOME/config/http.p12"
        rm -f "$CA_STORE" "$HTTP_STORE" "$BUILD/tls/root-ca.pem"

        # A real two-level chain rather than one self-signed certificate, for two
        # reasons: OpenSearch Security drops any certificate carrying
        # basicConstraints CA:true out of the server chain ("No certificates
        # found ... with alias"), and a Windows trust store wants a proper CA in
        # Trusted Root Certification Authorities, not a server certificate.
        "$KEYTOOL" -genkeypair \
            -alias ca \
            -keyalg RSA -keysize 2048 -validity 3650 \
            -dname "CN=DevSummit Local Test CA, OU=devsummit, O=devsummit, C=de" \
            -ext "bc:c=ca:true,pathlen:0" \
            -ext "ku:c=keyCertSign,cRLSign" \
            -keystore "$CA_STORE" -storetype PKCS12 \
            -storepass "$KEYSTORE_PASSWORD" -keypass "$KEYSTORE_PASSWORD" \
            >/dev/null 2>&1 || die "keytool failed to generate the CA"

        "$KEYTOOL" -genkeypair \
            -alias http \
            -keyalg RSA -keysize 2048 -validity 3650 \
            -dname "CN=$HOST, OU=devsummit, O=devsummit, C=de" \
            -keystore "$HTTP_STORE" -storetype PKCS12 \
            -storepass "$KEYSTORE_PASSWORD" -keypass "$KEYSTORE_PASSWORD" \
            >/dev/null 2>&1 || die "keytool failed to generate the node key pair"

        "$KEYTOOL" -exportcert -rfc -alias ca \
            -keystore "$CA_STORE" -storetype PKCS12 \
            -storepass "$KEYSTORE_PASSWORD" \
            -file "$BUILD/tls/root-ca.pem" >/dev/null 2>&1 \
            || die "keytool failed to export the CA certificate"

        "$KEYTOOL" -certreq -alias http \
            -keystore "$HTTP_STORE" -storetype PKCS12 \
            -storepass "$KEYSTORE_PASSWORD" 2>/dev/null \
            | "$KEYTOOL" -gencert -alias ca \
                -keystore "$CA_STORE" -storetype PKCS12 \
                -storepass "$KEYSTORE_PASSWORD" \
                -validity 3650 -rfc \
                -ext "san=$SAN" \
                -ext "bc:c=ca:false" \
                -ext "ku:c=digitalSignature,keyEncipherment" \
                -ext "eku=serverAuth" \
                > "$BUILD/tls/http-cert.pem" 2>/dev/null \
            || die "keytool failed to sign the node certificate"

        # Importing the reply needs the whole chain in one file, and the CA has
        # to be a known entry in the keystore first.
        "$KEYTOOL" -importcert -noprompt -alias ca \
            -file "$BUILD/tls/root-ca.pem" \
            -keystore "$HTTP_STORE" -storetype PKCS12 \
            -storepass "$KEYSTORE_PASSWORD" >/dev/null 2>&1 \
            || die "keytool failed to import the CA into the node keystore"

        cat "$BUILD/tls/http-cert.pem" "$BUILD/tls/root-ca.pem" \
            > "$BUILD/tls/http-chain.pem"
        "$KEYTOOL" -importcert -noprompt -alias http \
            -file "$BUILD/tls/http-chain.pem" \
            -keystore "$HTTP_STORE" -storetype PKCS12 \
            -storepass "$KEYSTORE_PASSWORD" >/dev/null 2>&1 \
            || die "keytool failed to import the signed node certificate"

        # Replace the demo HTTP certificate settings the installer appended.
        # Appending instead would leave duplicate YAML keys, which OpenSearch
        # refuses to parse - the settings have to be edited out, not overridden.
        sed -i '/^plugins\.security\.ssl\.http\.pem/d' "$CONFIG"
        cat >> "$CONFIG" <<EOF

# Generated HTTPS certificate, replacing the demo one whose root CA expired on
# 2023-09-28. Transport TLS still uses the demo certificates: they run to 2033
# and a single node never opens a transport connection to a peer. Only the HTTP
# layer is what ArcGIS - and every other client - actually validates.
plugins.security.ssl.http.keystore_filepath: http.p12
plugins.security.ssl.http.keystore_type: PKCS12
plugins.security.ssl.http.keystore_alias: http
plugins.security.ssl.http.keystore_password: $KEYSTORE_PASSWORD
plugins.security.ssl.http.clientauth_mode: NONE
EOF
        CERT_NOTE="generated, valid 10 years, SAN $SAN"
    else
        cp "$OS_HOME/config/root-ca.pem" "$BUILD/tls/root-ca.pem"
        log "keeping the demo certificates (--demo-certs)"
        log "  WARNING: their root CA expired on 2023-09-28. Clients will fail with"
        log "  'certificate has expired'. This is the upstream default, not a bug here."
        CERT_NOTE="OpenSearch demo certificate - EXPIRED root CA (2023-09-28)"
    fi

    log "configured WITH TLS and basic auth: https://$HOST:9200"
    log "  user     : admin"
    log "  password : $PASSWORD"
    log "  CA cert  : build/tls/root-ca.pem ($CERT_NOTE)"
    log ""
    log "  The CA is a private one. ArcGIS Pro will refuse the connection until"
    log "  build/tls/root-ca.pem is imported into the Windows certificate store"
    log "  under Trusted Root Certification Authorities."
fi

# State the other scripts read, so nobody has to remember which mode this is.
cat > "$BUILD/cluster.env" <<EOF
OPENSEARCH_HOME=$OS_HOME
OPENSEARCH_VERSION=$VERSION
CLUSTER_MODE=$MODE
CLUSTER_HOST=$HOST
CLUSTER_SCHEME=$([ "$MODE" = "insecure" ] && echo http || echo https)
CLUSTER_PORT=9200
EOF

log ""
log "done. Next:"
log "  ./scripts/run_opensearch.sh start"
if [ "$MODE" = "insecure" ]; then
    log "  python3 scripts/index_stations.py --recreate --host http://$HOST:9200 --no-auth"
else
    log "  python3 scripts/index_stations.py --recreate --host https://$HOST:9200 --ca-cert build/tls/root-ca.pem"
fi

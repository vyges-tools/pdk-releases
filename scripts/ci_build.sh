#!/usr/bin/env bash
# Build ONE ciel PDK family from its Vyges mirror and publish its per-library release.
#
# Runs on the runner: resolves the source commit and SKIPS if that commit is already
# released (unless FORCE=true) — so a skip costs NO Nix work. Only an actual build enters
# the shared Nix shell (ciel + magic + klayout + ghr), whose closure is cached across runs.
#
# Usage: ci_build.sh <family>   Env: FORCE (true|''), GH_TOKEN.
set -uo pipefail

f="${1:?usage: ci_build.sh <family>}"
case "${f}" in
  sky130|gf180mcu) m=open_pdks;    b=master; s=OPDKS ;;
  ihp-sg13g2)      m=ihp-open-pdk; b=main;   s=IHP ;;
  *) echo "::error::unknown family ${f}"; exit 1 ;;
esac

v=$(git ls-remote "https://github.com/vyges-tools/${m}.git" "${b}" | awk 'NR==1{print $1}')
[ -z "${v}" ] && { echo "::error::${f}: cannot resolve ${m}@${b}"; exit 1; }
tag="${f}-${v}"

if [ "${FORCE:-false}" != "true" ] && \
   gh release view "${tag}" --repo vyges-tools/pdk-releases >/dev/null 2>&1; then
  echo "::notice::${tag} already released — ${f} source unchanged, skipping (no build)"
  exit 0
fi

echo "=== building ${f} @ ${m} ${v} ==="
unset OPDKS_REPO_OWNER OPDKS_REPO_NAME IHP_REPO_OWNER IHP_REPO_NAME
if [ "${s}" = OPDKS ]; then
  export OPDKS_REPO_OWNER=vyges-tools OPDKS_REPO_NAME="${m}"
else
  export IHP_REPO_OWNER=vyges-tools IHP_REPO_NAME="${m}"
fi
root="${PWD}/pdk-root-${f}"; mkdir -p "${root}"

if nix shell \
     'github:fossi-foundation/ciel' \
     'github:fossi-foundation/nix-eda#magic' \
     'github:fossi-foundation/nix-eda#klayout' \
     'nixpkgs#ghr' \
     --accept-flake-config \
     --command bash -c "
       set -e
       ciel build --pdk-family '${f}' --pdk-root '${root}' --jobs \$(nproc) '${v}'
       ciel push  --pdk-family '${f}' --pdk-root '${root}' --owner vyges-tools --repository pdk-releases '${v}'
     "; then
  echo "${f}: published ${tag}"
else
  echo "::error::${f} build/push failed"
  exit 1
fi

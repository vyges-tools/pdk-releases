#!/usr/bin/env bash
# Build the selected ciel PDK families and publish per-library releases — run INSIDE one
# shared Nix shell (ciel + magic + klayout + ghr), so all families reuse a single Nix
# install + closure. Skips a family whose source commit is already released (idempotent;
# last release stays) unless FORCE=true.
#
# Env: FAMILY (sky130|gf180mcu|ihp-sg13g2|all|''), FORCE (true|''), GH_TOKEN.
set -uo pipefail

REQ="${FAMILY:-all}"
[ -z "${REQ}" ] && REQ=all
if [ "${REQ}" = all ]; then FAMILIES="sky130 gf180mcu ihp-sg13g2"; else FAMILIES="${REQ}"; fi

fail=0
for f in ${FAMILIES}; do
  # source per family (portable: no bash-4 assoc arrays)
  case "${f}" in
    sky130)     m=open_pdks;    b=master; s=OPDKS ;;
    gf180mcu)   m=open_pdks;    b=master; s=OPDKS ;;
    ihp-sg13g2) m=ihp-open-pdk; b=main;   s=IHP ;;
    *) echo "::error::unknown family ${f}"; fail=1; continue ;;
  esac

  v=$(git ls-remote "https://github.com/vyges-tools/${m}.git" "${b}" | awk 'NR==1{print $1}')
  if [ -z "${v}" ]; then echo "::error::${f}: could not resolve ${m}@${b}"; fail=1; continue; fi
  tag="${f}-${v}"

  if [ "${FORCE:-false}" != "true" ] && \
     gh release view "${tag}" --repo vyges-tools/pdk-releases >/dev/null 2>&1; then
    echo "::notice::${tag} already released — ${f} source unchanged, skipping"
    continue
  fi

  echo "=== building ${f} @ ${m} ${v} ==="
  unset OPDKS_REPO_OWNER OPDKS_REPO_NAME IHP_REPO_OWNER IHP_REPO_NAME
  if [ "${s}" = OPDKS ]; then
    export OPDKS_REPO_OWNER=vyges-tools OPDKS_REPO_NAME="${m}"
  else
    export IHP_REPO_OWNER=vyges-tools IHP_REPO_NAME="${m}"
  fi

  root="${PWD}/pdk-root-${f}"; mkdir -p "${root}"
  if ciel build --pdk-family "${f}" --pdk-root "${root}" --jobs "$(nproc)" "${v}" \
     && ciel push --pdk-family "${f}" --pdk-root "${root}" \
                  --owner vyges-tools --repository pdk-releases "${v}"; then
    echo "${f}: published ${tag}"
  else
    echo "::error::${f} build/push failed"; fail=1
  fi
done

exit "${fail}"

#!/usr/bin/env python3
# Copyright 2026 Vyges. All Rights Reserved. Apache-2.0.
"""Generic PDK packager — emit ciel-compatible per-library tarball releases from
*any* PDK source tree.

This is the non-ciel counterpart to `ciel push`: for PDKs ciel can't build
(icsprout55 today; NDA / customer PDKs later) it produces the **same release
artifacts** so pdk-store sees one consistent shape across every PDK —

    <family>-<version>            # release tag
      common.tar.zst              # shared / tech collateral
      <library>.tar.zst           # one per cell library

Manifest-driven (JSON):

    { "family": "icsprout55",
      "common":   ["prtech", "libs.tech"],
      "libraries": { "icsprout55_sc": ["libs.ref/icsprout55_sc"] } }

Packs only by default; pass --owner/--repository (+ a GITHUB_TOKEN) to publish via
`ghr`, exactly as `ciel push` does (tag `<family>-<version>`, commitish `releases`).
Std-lib only; shells out to `tar` + `zstd` (+ `ghr` for upload).
"""
import argparse
import json
import os
import subprocess
import sys


def tar_zst(source, paths, out_path):
    """tar `paths` (relative to `source`) and zstd-compress to `out_path`."""
    missing = [p for p in paths if not os.path.exists(os.path.join(source, p))]
    if missing:
        raise FileNotFoundError(f"{out_path}: not found under {source}: {missing}")
    with open(out_path, "wb") as out:
        tar = subprocess.Popen(["tar", "-cf", "-", "-C", source, *paths], stdout=subprocess.PIPE)
        zst = subprocess.Popen(["zstd", "-q", "-c"], stdin=tar.stdout, stdout=out)
        tar.stdout.close()
        zrc = zst.wait()
        trc = tar.wait()
        if trc != 0 or zrc != 0:
            raise RuntimeError(f"{out_path}: tar={trc} zstd={zrc}")
    return out_path


def pack(source, manifest, version, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    tarballs = []
    common = manifest.get("common", [])
    if common:
        tarballs.append(tar_zst(source, common, os.path.join(out_dir, "common.tar.zst")))
    for lib, paths in manifest.get("libraries", {}).items():
        tarballs.append(tar_zst(source, paths, os.path.join(out_dir, f"{lib}.tar.zst")))
    if not tarballs:
        raise SystemExit("manifest produced no tarballs (need `common` and/or `libraries`)")
    print(f"packed {len(tarballs)} tarball(s) for {manifest['family']}-{version}:")
    for t in tarballs:
        print(f"  {os.path.basename(t)}  ({os.path.getsize(t)} bytes)")
    return tarballs


def publish(tarballs, family, version, owner, repository):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("publish needs GITHUB_TOKEN in the environment")
    tag = f"{family}-{version}"
    body = f"{family} packaged by the Vyges generic PDK packager"
    for t in tarballs:
        subprocess.check_call([
            "ghr", "-owner", owner, "-repository", repository, "-token", token,
            "-body", body, "-commitish", "releases", "-replace", tag, t,
        ])
    print(f"published {tag} -> {owner}/{repository}")


def main():
    ap = argparse.ArgumentParser(description="Generic ciel-compatible PDK packager")
    ap.add_argument("--source", required=True, help="PDK source tree (e.g. a cloned mirror)")
    ap.add_argument("--manifest", required=True, help="packaging manifest (JSON)")
    ap.add_argument("--version", required=True, help="version / source commit (the release tag suffix)")
    ap.add_argument("--out", default="dist", help="output directory for tarballs")
    ap.add_argument("--owner", help="GitHub owner to publish to (enables upload)")
    ap.add_argument("--repository", help="GitHub repo to publish to (enables upload)")
    args = ap.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)
    if "family" not in manifest:
        raise SystemExit("manifest missing `family`")

    tarballs = pack(args.source, manifest, args.version, args.out)
    if args.owner and args.repository:
        publish(tarballs, manifest["family"], args.version, args.owner, args.repository)
    else:
        print("(pack-only; pass --owner/--repository to publish via ghr)", file=sys.stderr)


if __name__ == "__main__":
    main()

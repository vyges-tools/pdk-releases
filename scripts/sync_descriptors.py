#!/usr/bin/env python3
# Copyright 2026 Vyges. All Rights Reserved. Apache-2.0.
"""Inject Vyges PDK descriptors (`<name>.vyges-pdk.json`) into their mirror repos.

The PDK analogue of `vyges-metadata.json` in an IP repo: each mirror repo carries the
descriptor for the PDK it hosts, at the repo root, so the mirror is self-describing and
the release CI bundles it from there.

Each descriptor self-identifies its mirror via `upstream.mirror`, e.g.

    "upstream": { "mirror": "github.com/vyges-tools/ihp-open-pdk", ... }

so placement is data-driven, not hand-mapped. One mirror may carry several descriptors
(`open_pdks` -> `sky130a.vyges-pdk.json` + `gf180mcu.vyges-pdk.json`). Descriptors change rarely, so
this is an occasional sync, not a per-commit step.

    # source = the public catalog's descriptors; mirrors = a dir of checked-out mirrors
    sync_descriptors.py --descriptors ../pdk-catalog/descriptors --mirrors ../mirrors
    sync_descriptors.py --descriptors ../pdk-catalog/descriptors --mirrors ../mirrors --write

Dry-run by default; `--write` copies. Committing/pushing each mirror is left to you.
Std-lib only.
"""
import argparse
import json
import os
import shutil
import sys


def mirror_basename(descriptor):
    """`github.com/vyges-tools/ihp-open-pdk` -> `ihp-open-pdk` (the repo dir name)."""
    mirror = descriptor.get("upstream", {}).get("mirror", "")
    return mirror.rstrip("/").split("/")[-1] if mirror else ""


def main():
    ap = argparse.ArgumentParser(description="Inject <name>.vyges-pdk.json into mirror repos")
    ap.add_argument("--descriptors", required=True,
                    help="dir of *.vyges-pdk.json (e.g. a pdk-catalog/descriptors checkout)")
    ap.add_argument("--mirrors", required=True,
                    help="parent dir holding mirror-repo checkouts, each named by its repo")
    ap.add_argument("--write", action="store_true", help="actually copy (default: dry-run)")
    args = ap.parse_args()

    names = sorted(n for n in os.listdir(args.descriptors) if n.endswith(".vyges-pdk.json"))
    if not names:
        raise SystemExit(f"no *.vyges-pdk.json found under {args.descriptors}")

    placed = skipped = 0
    for name in names:
        src = os.path.join(args.descriptors, name)
        with open(src) as fh:
            descriptor = json.load(fh)
        repo = mirror_basename(descriptor)
        if not repo:
            print(f"  skip {name}: no upstream.mirror", file=sys.stderr)
            skipped += 1
            continue
        repo_dir = os.path.join(args.mirrors, repo)
        if not os.path.isdir(repo_dir):
            print(f"  skip {name}: mirror checkout {repo}/ not found under {args.mirrors}",
                  file=sys.stderr)
            skipped += 1
            continue
        dest = os.path.join(repo_dir, name)
        print(f"  [{'WRITE' if args.write else 'DRY'}] {name} -> {repo}/{name}")
        if args.write:
            shutil.copyfile(src, dest)
        placed += 1

    verb = "wrote" if args.write else "would write"
    print(f"{verb} {placed}; skipped {skipped}")
    if not args.write and placed:
        print("(dry-run; re-run with --write, then commit + push each mirror)")


if __name__ == "__main__":
    main()

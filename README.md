# vyges-tools/pdk-releases

Vyges-built open-PDK releases — the output of building [open_pdks](https://github.com/vyges-tools/open_pdks)
in CI, packaged exactly like [fossi-foundation/ciel-releases](https://github.com/fossi-foundation/ciel-releases)
so the same tooling consumes them. Vyges owns both the **inputs** (the open_pdks mirror)
and the **outputs** (these releases),
using [`ciel`](https://github.com/fossi-foundation/ciel) as the commodity builder — the
same way the flow uses OpenROAD / Yosys / Magic as commodity steps.

## Release format (ciel-compatible)

- **Tag:** `<family>-<open_pdks_commit>` — e.g. `sky130-<sha>`, `gf180mcu-<sha>`.
- **Assets:** per-library zstd tarballs — `common.tar.zst` plus one per cell library
  (`sky130_fd_sc_hd.tar.zst`, `sky130_fd_pr.tar.zst`, …), so a consumer downloads only the
  libraries it needs.

## How it's built — two paths, one artifact shape

The release format above is universal; the *builder* depends on the PDK.

**1. ciel families — `.github/workflows/build-release.yml`** (weekly + `workflow_dispatch`)
for the PDKs ciel knows (`sky130`, `gf180mcu` from open_pdks; `ihp-sg13g2` from its own
repo):

1. resolves the source commit from the Vyges mirror;
2. in a Nix shell with `ciel` + the EDA toolchain (`magic`, `klayout`) + `ghr`, runs
   **`ciel build`** with the source repo pointed at the Vyges mirror
   (`OPDKS_REPO_*` for sky130/gf180, `IHP_REPO_*` for ihp), then
3. **`ciel push`** packages the per-library tarballs and publishes here.

> A full sky130 build is heavy (≈1–2 h, needs the magic toolchain); gf180 and ihp are
> lighter. Validate on the first manual dispatch.

**2. Generic packager — `.github/workflows/package-release.yml`** (`workflow_dispatch`)
for PDKs ciel can't build (`icsprout55` today; NDA / customer PDKs later):
`scripts/pack_pdk.py` clones the mirror and packs it per `manifests/<pdk>.json` into the
**same** `common.tar.zst` + `<library>.tar.zst` shape, then publishes via `ghr`. This is
how every non-ciel PDK still lands as consistent artifacts pdk-store can consume the same
way. icsprout55 is mirrored at [`vyges-tools/icsprout55`](https://github.com/vyges-tools/icsprout55)
(from `openecos-projects/icsprout55-pdk`); dispatching this workflow packs `prtech` +
`IP/STD_cell` + `IP/IO` into a release here.

## The PDK descriptor (`<name>.vyges-pdk.json`)

Each release also carries its **Vyges PDK descriptor** — the PDK analogue of
`vyges-metadata.json` in an IP repo. The descriptor lives at the **root of the mirror repo**
(`vyges-tools/<mirror>/<name>.vyges-pdk.json`, e.g. `ihp-open-pdk/ihp_sg13g2.vyges-pdk.json`; `open_pdks`
carries both `sky130a.vyges-pdk.json` + `gf180mcu.vyges-pdk.json`), so the mirror is self-describing, and
the build CI bundles it from there:

- **standalone release asset** `<name>.vyges-pdk.json` — the uniform shape **pdk-store reads** (both
  the ciel and generic paths attach it); and
- **inside `common.tar.zst`** as well (generic packager — manifest `descriptor` field).

Bundling is **best-effort**: until a mirror carries the descriptor it is simply absent and the
pipeline stays green; the next release picks it up automatically. The descriptor is
schema-validated (`vyges-ip-internal/pdk_spec`) and published, byte-identical, via the public
[`vyges-tools/pdk-catalog`](https://github.com/vyges-tools/pdk-catalog) — the source to inject
into the mirrors with `scripts/sync_descriptors.py` (descriptors change rarely):

```sh
# place <name>.vyges-pdk.json into each mirror checkout, keyed by the descriptor's upstream.mirror
scripts/sync_descriptors.py --descriptors ../pdk-catalog/descriptors --mirrors ../mirrors        # dry-run
scripts/sync_descriptors.py --descriptors ../pdk-catalog/descriptors --mirrors ../mirrors --write
```

## Consuming

- **vyges pdk-store:** `fetch` pulls the per-library tarballs for sky130 / gf180 from here
  (the descriptors' `source: local` + open_pdks `upstream`), plus the `<name>.vyges-pdk.json`
  descriptor asset — so a fetched PDK arrives self-describing.
- **ciel:** the release format is ciel-native, so ciel can be pointed at this repo too.

---
© Vyges 2026. All Rights Reserved. Built from open_pdks (Apache-2.0); each PDK remains
under its own upstream license.

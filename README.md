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

## How it's built

`.github/workflows/build-release.yml` (weekly + manual `workflow_dispatch`):

1. resolves the open_pdks commit from the Vyges mirror (`vyges-tools/open_pdks@master`);
2. in a Nix shell providing `ciel` + the EDA toolchain (`magic`, `klayout`) + `ghr`,
   runs **`ciel build`** with `OPDKS_REPO_OWNER/NAME` pointed at the Vyges mirror, then
3. **`ciel push`** packages the per-library tarballs and publishes the release here.

Builds `sky130` and `gf180mcu` (both produced by open_pdks). `ihp_sg13g2` is **not** built
here — it ships from its own upstream and is mirrored at
[`vyges-tools/ihp-open-pdk`](https://github.com/vyges-tools/ihp-open-pdk).

> A full sky130 build is heavy (≈1–2 h, needs the magic toolchain). The workflow models
> ciel's `build`/`push` process; validate it on the first manual dispatch and adjust the
> Nix toolchain attributes if needed.

## Consuming

- **vyges pdk-store:** `fetch` pulls the per-library tarballs for sky130 / gf180 from here
  (the descriptors' `source: local` + open_pdks `upstream`).
- **ciel:** the release format is ciel-native, so ciel can be pointed at this repo too.

---
© Vyges 2026. All Rights Reserved. Built from open_pdks (Apache-2.0); each PDK remains
under its own upstream license.

# Versioning policy

Cutaway follows [Semantic Versioning 2.0](https://semver.org). The version
lives in two places that **must stay in lockstep**:

- `version.json` (`"version": "X.Y.Z"`)
- `Cutaway.manifest` (`"version": "X.Y.Z"`)

The updater compares the GitHub release tag (e.g. `v0.2.0`) against
`version.json`'s value. The manifest version is what Fusion shows in its
*Scripts and Add-Ins* dialog.

## When to bump which number

Pre-1.0 (where we are now), interpret the rules slightly looser:
public-facing breakage is allowed, but we should still distinguish "this
broke things for users" from "this added stuff" from "this fixed stuff".

| Change | Bump |
|--------|------|
| Bug fix, doc fix, internal refactor with no behavior change | **patch** (`0.1.0` → `0.1.1`) |
| New importer feature, new button, new supported filename format | **minor** (`0.1.0` → `0.2.0`) |
| Filename schema change that older zips can't be imported with | **major** (`0.1.0` → `1.0.0`) |
| Removed feature that some user might rely on | **major** |
| Manifest `id` UUID change (don't do this without a very good reason) | **major** |

## Tags

- Git tags are prefixed `v`: `v0.2.0`. The updater strips the prefix when
  comparing.
- Tags must point at a commit on `main` (the release workflow only fires on
  tag pushes).
- Don't reuse a tag. If you need to fix a bad release, cut a new patch
  release; the broken one stays in history for traceability.

## Pre-releases

GitHub supports marking a release as *pre-release*. The updater
intentionally only checks the **latest non-pre-release** tag, so if you mark
something as pre-release, users won't get prompted to update to it.

This is the rollback mechanism: if `v0.2.1` is broken, mark it as
pre-release and ship `v0.2.2`. Users on `v0.2.0` will jump straight to
`v0.2.2` and the broken release is invisible to them.

## version.json schema

```json
{
  "version": "0.2.0",
  "released": "2026-05-03",
  "notes": "Short human-readable summary."
}
```

- `version` (required, string): semver, no `v` prefix.
- `released` (required, string): ISO date, the day the release was tagged.
- `notes` (optional, string): one-line summary. The full changelog lives in
  `CHANGELOG.md`.

If you add fields, document them here and update `src/updater.py` if any
should affect update behavior.

# Releasing a new Cutaway version

End-to-end checklist for cutting a release. Follow it in order; the GitHub
Actions workflow takes care of building and publishing the zip.

## 1. Decide the version number

See [VERSIONING.md](VERSIONING.md) for the semver policy. TL;DR:
- **patch** (0.1.0 → 0.1.1): bug fixes, doc tweaks, no behavior changes.
- **minor** (0.1.0 → 0.2.0): new features, behavior changes that don't break
  existing users.
- **major** (0.1.0 → 1.0.0): breaking changes (filename schema break, removed
  features, manifest id change).

## 2. Update the version in two files

Both files MUST agree, or Fusion and the updater will disagree about what's
running.

```jsonc
// version.json
{
  "version": "0.2.0",
  "released": "2026-MM-DD",
  "notes": "Short human-readable summary of what changed."
}
```

```jsonc
// Cutaway.manifest
{
  ...
  "version": "0.2.0",
  ...
}
```

## 3. Update the changelog

Add a new entry to the top of `CHANGELOG.md`:

```markdown
## v0.2.0 — 2026-MM-DD

### Added
- ...

### Fixed
- ...

### Changed
- ...
```

## 4. Commit + tag + push

```bash
git add version.json Cutaway.manifest CHANGELOG.md
git commit -m "Release v0.2.0"
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

## 5. CI takes over

The `.github/workflows/release.yml` workflow fires on tag push. It:
- Bundles the add-in files into `cutaway-0.2.0.zip`.
- Creates a GitHub Release pointed at the tag, attaches the zip, and uses
  GitHub's auto-generated release notes from the commit log.

You can watch it run under the **Actions** tab on GitHub.

## 6. Verify

- Open the release page on GitHub. Confirm `cutaway-0.2.0.zip` is attached.
- Download the zip on a clean machine; run `install/install.bat` (or `.sh`).
- Open Fusion, run the add-in, confirm the importer button still appears
  and a known-good Cutaway zip imports correctly.

## 7. Users update

The next time any user starts Fusion with Cutaway enabled, the in-process
update check sees the new tag and surfaces the **Cutaway: Update to v0.2.0**
button in the MODIFY panel. Clicking it opens the GitHub release page; they
download the new zip and re-run the install script.

> *Future:* one-click update is on the roadmap (download → swap files →
> prompt restart). Out of scope for v1.

## Hotfix (urgent patch)

Same flow, but skip the changelog "Added/Changed" sections — write only
"Fixed". Bump the patch number, tag, push.

## Rolling back

If a release breaks something:
1. Cut a new patch release that reverts the offending change.
2. **Do not** delete the broken release — users who already updated need
   the install artifact to be reachable.
3. Mark the broken release as a *pre-release* on GitHub so it stops
   appearing as "Latest" — the updater only checks the latest tag.

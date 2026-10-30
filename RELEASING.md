# Releasing fledge

Publishing to Docker Hub (`fledgeiot/fledge`) and the Azure-hosted apt
repository (`https://packages.helinplatform.com/apt`) is **tag-driven**.
The workflow at [.github/workflows/publish-apt-azure.yml](.github/workflows/publish-apt-azure.yml)
will not push artifacts unless it runs on a ref of the form `refs/tags/v*`
(enforced via `if: startsWith(github.ref, 'refs/tags/v')` on the `publish`,
`docker-build`, and `docker-manifest` jobs, plus a tag-vs-`VERSION`
cross-check inside each). On a tag, the [Checker](.github/workflows/checker.yml)
(build, unit tests and a start/ping smoke test on Ubuntu 22.04 and 24.04) runs
first and must pass before anything is built.

Releases are cut from a `<X.Y.Z>RC` branch, merged, tagged `v<X.Y.Z>`, then
published via a GitHub Release event.

## Cutting a release

1. **Cut the RC branch off `develop`.**
   ```bash
   git checkout develop && git pull
   git checkout -b <X.Y.Z>RC
   ```
2. **Bump `VERSION`** on the RC branch. The file's `fledge_version=` line
   must match the tag you'll create (modulo the leading `v`). Bump
   `fledge_schema=` only if a schema migration is part of the release.
3. **Stabilize.** Final fixes and release notes go on the RC branch.
4. **Merge the RC branch back to develop via PR.** This is the merge
   commit the release tag will point at.
5. **Tag at the merge commit and push the tag.**
   ```bash
   git checkout develop && git pull
   git tag -a v<X.Y.Z> -m "fledge <X.Y.Z>"
   git push origin v<X.Y.Z>
   ```
6. **Create a GitHub Release** pointing at the tag. Publishing the Release
   fires `release: published`, which runs the workflow with
   `github.ref = refs/tags/v<X.Y.Z>` — gates open, artifacts publish.

The workflow's "Verify release tag matches VERSION file" step will fail
fast if the tag (e.g. `v3.1.0`) doesn't match `fledge_version=` in the
checked-out tree, or if the tag has been retargeted to a different commit
than the one the workflow is running on. That's the guard against shipping
artifacts from a feature branch.

## Break-glass: re-publishing an existing tag

If the Docker Hub or apt repo state for a previously-published version
needs to be rebuilt (e.g. a content drift, a registry blip, or an out-of-band
delete), re-run the workflow against the **tag ref** — not a branch.

From the Actions UI: `Run workflow` → ref dropdown → pick the `v<X.Y.Z>`
tag. The `docker buildx imagetools create` calls at
[.github/workflows/publish-apt-azure.yml#L470-L490](.github/workflows/publish-apt-azure.yml#L470-L490)
are idempotent on tag names; `:<version>`, `:<codename>`, and `:latest`
will be overwritten in place without disturbing the per-arch intermediary
digests.

`workflow_dispatch` from a branch ref will run only the `build` and
`repository-smoke` jobs — useful for testing the build path without
publishing, but **structurally cannot** push to Docker Hub or Azure Blob.

## What the workflow does on each trigger

| Trigger | `build` | `repository-smoke` | `publish` | `docker-build` | `docker-manifest` |
|---|---|---|---|---|---|
| `pull_request` (against paths) | ✅ | ✅ | ⛔ skipped | ⛔ skipped | ⛔ skipped |
| `workflow_dispatch` from a branch | ✅ | ✅ | ⛔ skipped | ⛔ skipped | ⛔ skipped |
| `workflow_dispatch` from a `v*` tag | ✅ | ✅ | ✅ | ✅ | ✅ |
| `release: published` (always tag-ref) | ✅ | ✅ | ✅ | ✅ | ✅ |

## Smoke testing

End-to-end smoke happens in **one place** — `repository-smoke`'s apt-install
loop, which exercises `apt-get install fledge` from a locally-served copy
of the apt metadata in a clean base-image container. That run covers
`bullseye amd64`, `bookworm amd64`, `bookworm arm64` (under QEMU), and
`jammy amd64`. The `build` job above it produces the .deb for every
codename×arch combo in the matrix; coverage gaps in the trimmed smoke
matrix (e.g. `bullseye arm64`, `noble amd64`) are absorbed by the fact that
every .deb still has to install cleanly during the apt smoke that's run
against the same content downstream.

After publish, a single `bookworm amd64` install against
`https://packages.helinplatform.com/apt` confirms the blob upload landed.

## Existing Docker Hub state

`fledgeiot/fledge:3.1.0` (and `:latest`, `:3.1.0-<codename>`) were
published from `feature/publish-apt-repo-azure` before the tag-ref gate
was in place. The content is functionally correct (the .debs were built
from a develop-based commit that is identical-in-effect to what `v3.1.0`
would produce) so the tags are left in place — overwriting them would
change digests for anyone who pinned. If strict tag-of-record provenance
matters later, re-run the workflow against the `v3.1.0` tag once the
gates are merged.

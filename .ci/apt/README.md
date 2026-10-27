# `.ci/apt/` — apt repository metadata and signing

`build_repo.sh` generates the repository tree, `test_repo.sh` installs from it in a
clean container, and `sign_release.py` signs the `Release` file with the archive
key held in Azure Key Vault.

## `build_repo.sh`

```
build_repo.sh INPUT_DIR REPO_DIR
```

Writes `pool/${CODENAME}/${COMPONENT}/<initial>/<package>/` and the matching
`dists/${CODENAME}/` metadata. It is cumulative, so re-invoking it with a
different `CODENAME` against the same `REPO_DIR` makes the codenames coexist in
one tree. `dpkg-scanpackages` is pointed at a single codename's pool so a
bullseye-built `.deb` (`Depends: libboost-system1.74.0`) can never leak into the
bookworm (1.81.0) `Packages` file.

| Env | Default | Meaning |
|---|---|---|
| `CODENAME` | required | `bullseye`, `bookworm`, `jammy`, `noble` |
| `COMPONENT` | `main` | apt component |
| `ARCHES` | `amd64 arm64` | space-separated architectures to index |
| `ORIGIN` | `Helin` | `Release` Origin field |
| `LABEL` | `Fledge` | `Release` Label field |

## Why a pool file is never rewritten

`packages.helinplatform.com` is Cloudflare in front of the storage account.
`dists/` is served with `max-age=60` and revalidates, so new metadata appears
almost at once. `pool/` is served with `max-age=86400`, which is correct only if
a given `<package>_<version>_<arch>.deb` URL never changes its bytes.

Publishing different bytes under a version that already exists therefore breaks
installs rather than updating them: the freshly generated `Packages` index
carries the new size and checksum while the edge keeps serving the old file, and
apt fails with `File has unexpected size`. It resolves itself once the edge copy
expires, up to 24 hours later, and only at the points of presence that cached
it — so the breakage is both long and geographically patchy. Purging the URLs by
hand is the only way to cut it short. That is also what apt semantics say
anyway: a version is immutable.

So `build_repo.sh` compares against the pool copy already in `REPO_DIR` and
refuses the write, with no override. Byte-identical writes still pass, which
keeps re-running a publish job idempotent. The fix for a rejected write is to
bump the version, which lands on a URL the edge has never seen.

## Why `sign_release.py` exists

Signing an apt repository normally means `gpg --detach-sign`, which needs the
private key on the machine doing the signing. Our archive key lives in a Key
Vault HSM and is non-exportable by design: it can be *used* but never retrieved.
`gpg` cannot drive a remote signer, so there is no way to hand it the key.

The script closes that gap. It builds the OpenPGP signature packet locally,
sends only the SHA-512 digest to Key Vault to be signed, and assembles the
result. The private key never leaves the HSM, and a compromised CI runner walks
away with signatures rather than the key.

That is the entire reason for the hand-rolled packet code below. Everything else
follows from having to construct by hand what `gpg` would normally do.

## Key hierarchy

Two RSA-4096 keys, generated in an offline ceremony:

- **L1 root**, certify-only. Never online. Its only job is to certify L2.
- **L2 signing subkey**, sign-only. Imported into Key Vault. This is what signs
  releases.

`helin-archive-keyring.gpg` is the public half of both, published to the apt
repo as `fledge.gpg` and pinned by devices via `signed-by=`. Rotating L2 does
not change the keyring's identity, so devices keep trusting the archive across
a rotation.

## What the script does

```
sign --in <Release> --out <Release.gpg> --keyring <fledge.gpg>
```

1. **Fetch the public key** from Key Vault (`KeyVaultSigner`): the RSA modulus `n`
   and exponent `e`.
2. **Find the matching key in the keyring** (`subkey_fpr`). It walks the keyring's
   packets looking for a public key (tag 6) or public subkey (tag 14) whose `n`
   and `e` match what Key Vault returned, then computes that key's fingerprint.
   If nothing matches it refuses to sign. This is the guard that makes it
   impossible to emit a signature claiming an issuer the vault key does not own,
   for example after pointing `--key-name` at the wrong key.
3. **Build the signature packet** (`make_signature`) and hash it. The digest
   covers the file contents followed by the signature's own header and trailer,
   which is what binds the signature to both the data and its metadata.
4. **Sign the digest** in Key Vault using `RS512`. Azure's `RS512` is PKCS#1 v1.5
   over SHA-512, which is exactly the RSA signature construction OpenPGP
   specifies. No conversion is needed.
5. **Assemble and armor** the packet into `Release.gpg`.

## Which spec

We produce **version 4** packets, which is also the only interoperable option
here: apt verifies with `gpgv` from GnuPG. Section references below are to
RFC 4880.

## The magic numbers

Listed here so nobody has to reverse-engineer them:

| Value | Meaning |
|---|---|
| `0xC0 \| tag` | new-format packet header (§4.2) |
| tag 2 | signature packet |
| tags 6 / 14 | public key / public subkey packet |
| sig type `0x00` | signature over a binary document, correct for a detached `Release.gpg` |
| pubkey algo `1` | RSA |
| hash algo `0x0a` | SHA-512 |
| hashed subpacket 2 | signature creation time |
| hashed subpacket 33 | issuer fingerprint |
| unhashed subpacket 16 | issuer key ID |
| `0x99` prefix in `fingerprint()` | fingerprint is SHA-1 over `0x99 \|\| len \|\| key body` (§12.2) |
| `\x04\xff` trailer | v4 signature trailer, followed by the header length |
| `digest[:2]` | leading two octets of the hash, a quick corruption check |

SHA-1 in `fingerprint()` is not a security choice. OpenPGP v4 fingerprints are
defined as SHA-1 over the key material; it identifies a key, it does not protect
anything.

## Dependencies and auth

`azure-identity` and `azure-keyvault-keys`, pinned in `requirements.txt`.
Authentication is `DefaultAzureCredential`, so the same code works from a
workload-identity CI runner, a managed identity, or a developer's `az login`
session with no change.

A 403 from Key Vault almost always means the identity is missing **Key Vault
Crypto User**, not that the key is wrong.

## Testing without a Key Vault

`KeyVaultSigner` is only used through two members, `n`/`e` and `sign_digest()`.
Anything exposing those can be substituted, so the packet construction can be
tested end to end against a locally generated RSA key and verified with `gpgv`,
with no cloud dependency. That seam is also what would let a different backend
(AWS KMS, GCP KMS) drop in.

## Verifying the output

```sh
gpgv --keyring ./fledge.gpg Release.gpg Release
```

The publish workflow runs exactly this on every codename before uploading, so a
malformed signature fails the release instead of shipping a repository that
every device rejects.

To inspect what was produced:

```sh
gpg --list-packets Release.gpg
```
## Keyring input format

`sign_release.py` reads binary OpenPGP keyrings containing v4 RSA
encrypt-or-sign keys only. Armored keyrings, v3/v6 keys, and partial packet
lengths are rejected. `build_repo.sh` and the workflows only ever feed it the
binary `helin-archive-keyring.gpg` from this directory, which satisfies that
contract by construction.

The workflows pass `--key-version` and `--expect-fingerprint` when the
`APT_SIGNING_KEY_VERSION` and `APT_SIGNING_KEY_FPR` environment variables are
set on the production environment, pinning the exact Key Vault key version and
the exact OpenPGP issuer so neither key rotation nor a keyring swap can change
the signer silently.

## Release candidates

A tag `v<VERSION>-rc.<n>` publishes a release candidate. `.ci/release/resolve_version.sh` maps the tag to the package version `<VERSION>~rc.<n>`, which sorts below the final `<VERSION>` and above the previous release, and to the image tag `<VERSION>-rc.<n>`.

Candidates go to a separate suite, `<codename>-rc`, signed with the same key and published through the same `production` gate. The suite's `Release` sets `NotAutomatic` and `ButAutomaticUpgrades` (`NOT_AUTOMATIC=yes` for `build_repo.sh`), so apt never picks a candidate unless asked: `apt install -t noble-rc fledge`. Stable `<codename>` suites are untouched.

Candidate images are pushed only as versioned `-slim` tags. `latest`, the bare version tags and the full images are never moved for a candidate.

Plugin candidates use the same convention. `publish-plugin-apt.yml` sends any version containing `~rc.` to the `-rc` suite.

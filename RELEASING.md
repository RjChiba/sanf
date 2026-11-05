# Releasing

Releases are published to [PyPI](https://pypi.org/project/sanf/) by
`.github/workflows/release.yml` when a `v*.*.*` tag is pushed.

The workflow uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/):
PyPI accepts uploads from this repository's `release.yml` running in the `pypi`
environment, using a short-lived OIDC token. No PyPI API token is stored in
GitHub, and none should be added as a secret.

## Pipeline

```
push tag v1.2.0
  └─ test     (contents: read)    pytest
      └─ build    (contents: read)    tag is on main? tag == pyproject.toml == sanf/main.py?
          │                            python -m build, twine check --strict
          └─ publish  (id-token: write, environment: pypi — waits for approval)
                                       upload to PyPI with PEP 740 attestations
```

- Only the `publish` job can obtain a PyPI credential. It runs no repository
  code: it downloads the built files and uploads them.
- All actions are pinned to full commit SHAs. Dependabot
  (`.github/dependabot.yml`) proposes updates after a 14-day cooldown.
- Checkouts use `persist-credentials: false`, and the workflows use no
  `pull_request_target` or other triggers that run fork code with write access.

## One-time setup

### 1. PyPI: add the trusted publisher

On <https://pypi.org/manage/project/sanf/settings/publishing/>, add a GitHub
publisher:

| Field | Value |
|---|---|
| Owner | `RjChiba` |
| Repository name | `sanf` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Then, on the same account:

- Delete any API tokens that were used for manual uploads of 1.0.0 / 1.1.0
  (Account settings → API tokens), or at least any token scoped to `sanf`.
- Make sure two-factor authentication is enabled.

### 2. GitHub: create the `pypi` environment

Settings → Environments → New environment → `pypi`:

- **Required reviewers**: add yourself (and any co-maintainers). Each release then
  waits for an explicit approval before anything is uploaded.
- **Deployment branches and tags**: *Selected branches and tags* → add a **tag**
  rule `v*`. The environment then cannot be used from branches.
- Do not add any secrets to it.

### 3. GitHub: protect release tags

Settings → Rules → Rulesets → New tag ruleset:

- Target tags: include `v*`
- Rules: *Restrict creations*, *Restrict updates*, *Restrict deletions*,
  *Block force pushes*
- Bypass list: repository admins only

### 4. GitHub: Actions settings

Settings → Actions → General:

- *Workflow permissions*: **Read repository contents and packages permissions**
- *Allow GitHub Actions to create and approve pull requests*: off
- *Approval for running fork pull request workflows*: **Require approval for
  all external contributors**
- Optionally, *Require actions to be pinned to a full-length commit SHA*

## Releasing a version

1. On a branch, set the new version in **both** `pyproject.toml` and
   `sanf/main.py` (`FastAPI(..., version=...)`), and date the entry in
   `CHANGELOG.md`. Merge it into `main` through a pull request.
2. Tag the merge commit on `main` and push the tag:

   ```bash
   git switch main && git pull --ff-only
   ```

   ```bash
   git tag -a v1.2.0 -m "v1.2.0"
   ```

   ```bash
   git push origin v1.2.0
   ```

3. In the Actions tab, open the *Release* run and approve the `pypi`
   deployment once `test` and `build` have passed.
4. Check <https://pypi.org/project/sanf/>. Optionally, create a GitHub Release
   for the tag with the CHANGELOG entry.

A run fails without uploading anything if the tag is not on `main`, or if the
tag does not match `pyproject.toml` and `sanf/main.py`. In that case, delete the
tag, fix the version, and tag again. A version that has reached PyPI cannot be
uploaded again, so publish a new patch version instead.

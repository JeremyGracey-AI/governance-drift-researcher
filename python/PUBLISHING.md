# Publishing `governance-drift` to PyPI

Publishing uses **OIDC Trusted Publishing** — GitHub Actions authenticates to PyPI with a
short-lived token minted per run. No API token is stored anywhere. The `publish` job in
`.github/workflows/python.yml` runs only on a `v*` tag.

## One-time PyPI setup (you, in a browser)

1. Sign in at https://pypi.org.
2. Go to **Publishing** → **Add a pending publisher**
   (https://pypi.org/manage/account/publishing/).
3. Fill in exactly:
   - **PyPI Project Name:** `governance-drift`
   - **Owner:** `JeremyGracey-AI`
   - **Repository name:** `governance-drift-researcher`
   - **Workflow name:** `python.yml`
   - **Environment name:** `pypi`
4. Save. (A "pending" publisher creates the project on first successful publish — you do
   not need to pre-create the project or upload anything manually.)

## Release (per version)

```bash
# from the repo root, on main, with everything committed and CI green:
git tag v0.1.0
git push origin v0.1.0
```

The tag triggers the workflow: `test` (3.11/3.12/3.13) → `cleanroom` (build the wheel,
install it into an empty env, run `govdrift`, assert the SARIF) → `publish` (build + OIDC
upload to PyPI). Watch it at the repo's Actions tab.

## Verify

```bash
pip install governance-drift
govdrift scan --help
```

## Bumping versions

Edit `version` in both `pyproject.toml` and `src/governance_drift/__init__.py` (keep them
in sync), commit, then tag `vX.Y.Z`. PyPI rejects re-uploading an existing version, so a
version number is spent once — never reused.

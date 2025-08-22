# Publishing RVS to PyPI

This repository is configured with automated GitHub Actions workflows for publishing to PyPI.

## Automated Publishing Workflow

### How it works:
1. **Test Build**: Every push and PR triggers build tests across multiple OS and Python versions
2. **Release Publishing**: When you create a GitHub release, the package is automatically built and published to PyPI

### To publish a new version:

1. **Update the version** in `setup.py`:
   ```python
   version="2.0.4",  # Update this
   ```

2. **Commit and push** the version change:
   ```bash
   git add setup.py
   git commit -m "Bump version to 2.0.4"
   git push origin main
   ```

3. **Create a GitHub release**:
   - Go to https://github.com/rvs-rvs/rvs/releases
   - Click "Create a new release"
   - Tag version: `v2.0.4` (must match setup.py version)
   - Release title: `RVS v2.0.4`
   - Add release notes describing changes
   - Click "Publish release"

4. **Automatic publishing**: The GitHub Action will automatically:
   - Build the package
   - Run quality checks
   - Publish to PyPI
   - Update the release with PyPI link

## Prerequisites for Publishing

### GitHub Environment Setup:
1. Go to repository Settings → Environments
2. Create environment named `pypi`
3. Add protection rules (optional but recommended)

### PyPI Trusted Publishing:
1. Go to https://pypi.org/manage/account/publishing/
2. Add a new trusted publisher:
   - **PyPI Project Name**: `rvs`
   - **Owner**: `rvs-rvs`
   - **Repository name**: `rvs`
   - **Workflow filename**: `publish-to-pypi.yml`
   - **Environment name**: `pypi`

## Manual Publishing (if needed)

If you need to publish manually:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Check the package
python -m twine check dist/*

# Upload to PyPI (requires API token)
python -m twine upload dist/*
```

## Workflow Files

- `.github/workflows/publish-to-pypi.yml`: Handles automatic PyPI publishing on release
- `.github/workflows/test-build.yml`: Tests package builds on every push/PR

## Version Management

The version is managed in `setup.py`. Always update it before creating a release:
- Current version: `2.0.3`
- Next version should follow semantic versioning (e.g., `2.0.4`, `2.1.0`, `3.0.0`)
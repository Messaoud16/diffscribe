## Publishing DiffScribe as a Package

### Versioning
- Follow semantic versioning (`MAJOR.MINOR.PATCH`).
- Update `__version__` in `diffscribe/__init__.py` and `version` in `pyproject.toml`.
- Tag releases using `git tag vX.Y.Z` and push with `git push origin vX.Y.Z`.

### Build & Publish (PyPI or GitHub Packages)
1. Ensure you have `poetry` installed.
2. Build distribution artifacts:
   ```bash
   poetry build
   ```
3. Publish to your chosen registry:
   - **Test PyPI**: `poetry publish -r testpypi`
   - **PyPI**: `poetry publish --username __token__ --password <pypi-token>`
   - **GitHub Packages**:
     ```bash
     poetry config repositories.diffscribe https://maven.pkg.github.com/your-org/diffscribe
     poetry publish -r diffscribe --username YOUR_GH_USERNAME --password <github-token>
     ```

### Git-only Installation
For internal use without a package registry, tag the release and instruct consumers to install via:
```bash
pip install git+https://github.com/your-org/diffscribe.git@vX.Y.Z
```

### Release Checklist
- [ ] Update changelog / release notes.
- [ ] Bump versions.
- [ ] Run `pytest`.
- [ ] Build and publish artifacts.
- [ ] Push git tag.
- [ ] Notify dependent teams/repos.


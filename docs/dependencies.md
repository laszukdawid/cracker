# Dependency policy

Cracker supports Python 3.14 and uses `uv.lock` as the reproducible record of all resolved dependencies.

## Version constraints

- Runtime dependencies use a tested lower bound and an upper bound at the next expected breaking release.
- Development and build tools follow the same policy; exact versions remain recorded in `uv.lock`.
- Major upgrades are reviewed independently. Minor and patch upgrades may be grouped when the complete validation suite passes.
- PyQt remains on version 5. A migration to PyQt6 or PySide6 is a separate compatibility project.

## Updating dependencies

Dependabot checks uv and GitHub Actions dependencies weekly. Routine minor and patch Python updates are grouped; major updates remain separate.

For a manual update:

```shell
uv lock --upgrade-package <package>
make check
```

Commit `pyproject.toml` and `uv.lock` together whenever dependency constraints change. Commit only `uv.lock` when refreshing a compatible transitive or directly declared version without changing policy.

## Validation

Every dependency update must pass:

```shell
make check
```

Cloud backend changes should retain mocked request and credential tests. Desktop dependency changes must pass the Linux and macOS CI jobs.

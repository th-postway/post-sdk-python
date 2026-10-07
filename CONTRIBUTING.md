# Contributing

## Setup

```bash
uv sync        # Python 3.11+ (.python-version pins 3.11 for local work)
make check     # ruff format --check + ruff check + mypy --strict + unit tests
```

Other targets: `make test`, `make format`, `make lint`, `make typecheck`, `make build`, `make test-integration`.

## Layout

```
src/postway/__init__.py     public surface (__all__); tests/unit/test_package_surface.py snapshots it
src/postway/_client.py      PostwayMerchantClient
src/postway/_http.py        HttpPipeline, param(), Transport protocol, UrllibTransport
src/postway/_errors.py      error classes
src/postway/_validation.py  base URL / header / timeout / path-segment validation
src/postway/_environments.py, _files.py, _version.py
src/postway/resources/      one class per API area; methods map 1:1 to endpoints
src/postway/types/          TypedDict request/response types, one module per resource (same name), plus enums
tests/unit/core             client, HTTP pipeline and default-transport tests
tests/unit/resources        one file per resource, asserting method, URL, headers and body
tests/unit/support.py       fake transport and response builders
tests/integration           read-only live checks, skipped without credentials
```

## Conventions

- Modules are `snake_case`; resource and type modules share the same plural name (`order_shipments.py`).
- `TypedDict` keys use the wire names (`snake_case`) so payloads match the API schema. Keep the API's model names in docstring backticks.
- No runtime dependencies. Standard library only.
- `__version__` lives only in `src/postway/_version.py` (enforced by a test).
- Never log, never `print`, never read environment variables in `src/` (ruff's `T20` rule catches `print`).
- Formatting is ruff's (line length 120). Do not hand-format.

### Security rules

- `PostwayConfigError` messages never repeat the offending value.
- Every caller-supplied path segment goes through `param()` in `src/postway/_http.py`, so it is validated and shown as `:name` in errors.
- Header values go through the validators in `src/postway/_validation.py`.
- Redirects stay refused, and nothing is retried beyond the single 403 replay after a token refresh.
- No internal hostnames, ports, service names or private package names anywhere in code, comments, tests or docs. The only public hosts are the two in `src/postway/_environments.py`.

## Adding an endpoint

1. Add the request/response types to `src/postway/types/<resource>.py` and export them from `types/__init__.py` and `postway/__init__.py`.
2. Add the method to `src/postway/resources/<resource>.py`; wrap path parameters in `param()`.
3. Add a test to `tests/unit/resources/test_<resource>.py` asserting method, URL, headers and body.
4. Update the `__all__` snapshot, add a row to the method catalogue in `README.md`, and add a line under `Unreleased` in `CHANGELOG.md`.

## Integration tests

Read-only, skipped unless both variables are set:

```bash
POSTWAY_MERCHANT_BASE_URL=https://sandbox-post.postway.co.th/merchant \
POSTWAY_MERCHANT_ACCESS_TOKEN=... \
make test-integration
```

## Branches and releases

The repository uses git-flow with its default settings (no tag prefix):

| Branch | Purpose |
| --- | --- |
| `main` | released code; every release is a tag on it |
| `develop` | integration branch; open pull requests against it |
| `feature/*`, `bugfix/*` | work branches, started from `develop` |
| `release/<version>` | release preparation, started from `develop` |
| `hotfix/<version>` | urgent fix to a released version, started from `main` |

Versions are SemVer `MAJOR.MINOR.PATCH` with **no `v` prefix**, used as is in branch and tag names: `release/1.1.0` becomes tag `1.1.0`. The major stays `1`.

CI (`.github/workflows/ci.yml`) runs on pushes to `main`, `develop`, `release/**` and `hotfix/**`, and on every pull request. On `release/*` and `hotfix/*` it also fails unless the branch name is `MAJOR.MINOR.PATCH` and equals `__version__`. Dependabot opens its pull requests against `develop`.

### Releasing

1. `git flow release start 1.x.y` (from `develop`).
2. Bump `__version__` in `src/postway/_version.py`, move the `Unreleased` entries in `CHANGELOG.md` under `[1.x.y]` with today's date, and commit.
3. `git push -u origin release/1.x.y` and wait for CI.
4. `git flow release finish 1.x.y`: merges into `main`, tags `1.x.y` there, and merges back into `develop`.
5. `git push --atomic origin main develop 1.x.y`, then delete `release/1.x.y` on the remote if it is still there.

For an urgent fix, run the same steps with `git flow hotfix start 1.x.y` (from `main`) and `git flow hotfix finish 1.x.y`.

The `Publish` workflow (`.github/workflows/publish.yml`) runs only for tags matching `MAJOR.MINOR.PATCH`; a `v`-prefixed or pre-release tag does not start it. It checks that the tag is on `main` and equals `__version__`, runs `make check`, builds, and publishes to PyPI with trusted publishing (OIDC).

GitHub setup: a `pypi` environment, and a trusted publisher on PyPI for this repository, workflow `publish.yml` and environment `pypi`; no API token is stored. Limit the environment's deployment tags to `[0-9]*.[0-9]*.[0-9]*`.

Never move or reuse a published tag. If `Publish` fails for a transient reason, re-run it; otherwise fix forward with a hotfix and the next patch version.

# Demo

`quick_start.py` is a runnable version of the [README Quick start](../README.md#quick-start). It walks one Merchant flow with this repository's SDK. The Node SDK (the reference) and the .NET SDK ship the same demo.

1. `health.ping()`: public, so it works without a token.
2. `auth.account_info()`: store name and token expiry.
3. `shipment_providers.all()`: couriers the store may use.
4. `thailand.filter()`: postal areas for zip code `10500`.
5. `order_shipments.filter()`: the store's parcel count and the status of the latest five.
6. _Opt-in, sandbox only:_ `order_shipments.create()` followed by `labels.order_shipments()`, which saves the label to `demo/output/`.

The demo is **read-only by default** and targets **sandbox**, unlike the SDK, which defaults to production.

## Requirements

- Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).
- A merchant session access token. Postway issues it to your store; there is no token endpoint.

## Run

```bash
uv sync                                   # installs postway from src/ (editable) into .venv
export POSTWAY_ACCESS_TOKEN=...           # from your shell or secret manager, never committed
make demo                                 # same as: uv run python demo/quick_start.py
```

| Variable                                      | Required      | Meaning                                                                                                                               |
| --------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `POSTWAY_ACCESS_TOKEN`                        | for steps 2–6 | Merchant session token. `POSTWAY_MERCHANT_ACCESS_TOKEN` (used by integration tests) also works                                        |
| `POSTWAY_MERCHANT_BASE_URL`                   | no            | Base URL override. Default: `https://sandbox-post.postway.co.th/merchant`                                                             |
| `POSTWAY_DEMO_CREATE`                         | no            | `1` runs step 6                                                                                                                       |
| `POSTWAY_CLIENT_ID` / `POSTWAY_CLIENT_SECRET` | no            | The store's client credentials. Not read by the demo or the SDK: the API has no token endpoint, so authenticate with the access token |

The demo reads environment variables only. To keep them in a local `.env` (gitignored, never committed), load it first: `set -a; . ./.env; set +a; make demo`.

Without a token the demo pings, prints which variable to set, and exits with code 1. A 403 means the token is missing, unknown or expired.

## Creating a parcel (opt-in)

```bash
POSTWAY_DEMO_CREATE=1 make demo
```

Step 6 creates a **real sandbox parcel** from the Quick start payload. The courier is the first one `shipment_providers.all()` returns, and `my_tracking_no` is generated as `DEMO-<unix ms>`. `order_shipments.create` is not idempotent, so every run creates a new parcel. The demo refuses this step unless the base URL is the sandbox URL. The label is written to `demo/output/` (gitignored).

## Using the local SDK in another project

```bash
cd ../my-app
uv add --editable ../post-sdk-python      # or: pip install -e ../post-sdk-python
```

Then copy `quick_start.py` into that project and run it the same way.

## Checks

`make check` covers the demo: `ruff format --check`, `ruff check` (with `print` allowed only under `demo/`) and `mypy --strict`. The demo is not in the published sdist or wheel.

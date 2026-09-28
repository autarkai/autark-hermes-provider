# Autark provider for Hermes Agent

Connect [Autark](https://autark.ai) to Hermes Agent as a first-class provider —
no manual `context_length` pin, no custom-endpoint plumbing.

## What this gives you

Autark exposes routed **contracts**, not raw models:

| Contract | Purpose |
|---|---|
| `autark-agent` | agentic work — tool calling, long-horizon tasks |
| `autark-pro` | general reasoning |
| `autark-deep` | hard reasoning |
| `*-private` | same contracts with zero data retention |

Each contract resolves to whichever upstream model the router picks, and all of
them serve a **1M token context window**. This plugin teaches Hermes that, so the
window is correct the moment you connect.

## Install

```bash
git clone https://github.com/autarkai/autark-hermes-provider \
  ~/.hermes/plugins/model-providers/autark
```

Then set your key and select a contract:

```bash
echo 'AUTARK_API_KEY=autark_sk_...' >> ~/.hermes/.env
hermes model          # pick "Autark" → autark-agent
```

Verify:

```bash
hermes plugins validate ~/.hermes/plugins/model-providers/autark
```

## Why the profile overrides `get_model_context_length`

This is the non-obvious part, and it is why this plugin is not just a five-line
`ProviderProfile`.

Registering a profile is **not a pure addition**. `agent/model_metadata.py`
auto-extends its `_URL_TO_PROVIDER` map with every registered profile's hostname.
A base URL that resolves there counts as a *known provider*, and known providers
**skip** the generic live `/v1/models` context probe — on the grounds that a
provider's `/models` may report a provider-imposed limit rather than the true
window.

The profile hook is consulted *earlier* than that skip, so supplying the window
here keeps it correct. Without the override, installing this plugin would quietly
drop an unpinned client from 1,048,576 back to the 256,000 fallback — the exact
bug the plugin exists to prevent.

`tests/test_profile.py::TestNoRegression` pins this behaviour.

## Requirements

- Hermes Agent with the `model-providers` plugin surface (the `providers` module
  and `plugins/model-providers/` discovery).
- An Autark API key from <https://autark.ai/>.

## Development

The tests import `providers` and `agent.model_metadata` from a Hermes checkout,
so they must run **from that checkout** (not from this repo's directory):

```bash
cd /path/to/hermes-agent
./venv/bin/python -m pytest /path/to/autark-hermes-provider/tests/test_profile.py -q
```

Running them from inside this repo fails with `ModuleNotFoundError: agent` —
that is a working-directory issue, not a broken test.

## License

MIT

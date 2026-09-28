# Autark for Hermes Agent

Connect [Autark](https://autark.ai) to Hermes Agent in one command. No manual
`context_length` pin, no custom endpoint setup.

## What you get

Autark serves three contracts, each with a zero-data-retention variant:

| Contract | Use it for |
|---|---|
| `autark-agent` | Agentic work: tool calling, long-running tasks |
| `autark-pro` | General reasoning |
| `autark-deep` | Hard reasoning |
| `*-private` | The same three, zero data retention |

The best model handles every request, and all six contracts serve a 1M token
context window. This plugin tells Hermes that, so the window is right the moment
you connect.

## Install

```bash
git clone https://github.com/autarkai/autark-hermes-provider \
  ~/.hermes/plugins/model-providers/autark
```

Then set your key and pick a contract:

```bash
echo 'AUTARK_API_KEY=autark_sk_...' >> ~/.hermes/.env
hermes model          # pick "Autark" then autark-agent
```

Verify:

```bash
hermes plugins validate ~/.hermes/plugins/model-providers/autark
```

## Why this plugin overrides `get_model_context_length`

The short version: without this override, the plugin would make things worse.

Registering a profile is not a pure addition. `agent/model_metadata.py` adds
every registered profile's hostname to its `_URL_TO_PROVIDER` map. A base URL
found there counts as a known provider, and known providers skip the generic live
`/v1/models` context probe. Hermes assumes a provider's `/models` may report a
provider-imposed limit rather than the real window.

The profile hook runs earlier than that skip, so supplying the window here keeps
it correct. Without it, installing this plugin would drop an unpinned client from
1,048,576 back to the 256,000 fallback. That is the exact bug the plugin exists to
prevent.

`tests/test_profile.py::TestNoRegression` pins this.

## Requirements

- Hermes Agent with the `model-providers` plugin surface (the `providers` module
  and `plugins/model-providers/` discovery).
- An Autark API key from <https://autark.ai/>.

## Development

The tests import `providers` and `agent.model_metadata` from a Hermes checkout,
so they must run from that checkout, not from this repo's directory:

```bash
cd /path/to/hermes-agent
./venv/bin/python -m pytest /path/to/autark-hermes-provider/tests/test_profile.py -q
```

Running them from inside this repo fails with `ModuleNotFoundError: agent`. That
is a working-directory issue, not a broken test.

## License

MIT

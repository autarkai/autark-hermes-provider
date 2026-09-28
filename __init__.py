"""Autark provider profile for Hermes Agent.

Autark exposes routed *contracts* rather than raw models — ``autark-agent``,
``autark-pro``, ``autark-deep`` and their ``-private`` (ZDR) variants. A contract
resolves to whichever upstream model the router picks for the request, so its
context window is a property of the contract, not of any single model.

Why this profile overrides ``get_model_context_length``
-------------------------------------------------------
Registering a profile is not a pure addition: ``agent/model_metadata.py``
auto-extends ``_URL_TO_PROVIDER`` with every registered profile's hostname, and
a base URL that resolves there counts as a *known provider*. Known providers
**skip** the generic live ``/v1/models`` context probe (step 2 in
``get_model_context_length``) on the grounds that a provider's ``/models`` may
report a provider-imposed limit rather than the true window.

The profile hook is consulted earlier (step 1b) than that skip, so supplying the
window here keeps the value correct. Without this override, registering the
profile would quietly regress an unpinned client from 1,048,576 back to the
256,000 fallback — the exact bug this provider exists to avoid.
"""

from __future__ import annotations

from providers import register_provider
from providers.base import ProviderProfile

AUTARK_BASE_URL = "https://api.autark.ai/v1"

# The window every Autark contract currently serves. All contracts route to
# upstream models exposing a 1M window, and the API advertises this same value
# per contract in ``GET /v1/models``. Bump it when the routed pool's floor moves.
CONTRACT_CONTEXT_LENGTH = 1_048_576

# Public contract surface: 3 contracts x 2 ZDR states.
CONTRACTS: tuple[str, ...] = (
    "autark-agent",
    "autark-pro",
    "autark-deep",
    "autark-agent-private",
    "autark-pro-private",
    "autark-deep-private",
)


class AutarkProfile(ProviderProfile):
    """Autark: agent, pro and deep contracts behind one OpenAI-compatible endpoint."""

    def get_model_context_length(self, model: str) -> int | None:
        """Return the contract's window, or None to let the normal chain run.

        Returning None for an unrecognised id is deliberate: a model this
        profile does not know about should fall through to the generic
        resolution chain rather than inherit a contract's window.
        """
        if (model or "").strip().lower() in CONTRACTS:
            return CONTRACT_CONTEXT_LENGTH
        return None


autark = AutarkProfile(
    name="autark",
    aliases=("autark-ai",),
    display_name="Autark",
    description="Autark: agent, pro and deep contracts (1M context)",
    signup_url="https://autark.ai/",
    env_vars=("AUTARK_API_KEY", "AUTARK_BASE_URL"),
    base_url=AUTARK_BASE_URL,
    fallback_models=CONTRACTS,
    default_aux_model="autark-agent",
    supports_vision=True,
    model_capabilities={
        contract: {"context_length": CONTRACT_CONTEXT_LENGTH, "supports_vision": True}
        for contract in CONTRACTS
    },
)

register_provider(autark)

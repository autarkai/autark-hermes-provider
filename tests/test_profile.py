"""Tests for the Autark provider profile.

These run against the real registry (the plugin is installed into a throwaway
``HERMES_HOME`` by the fixture), so they exercise the same discovery path a user
hits — not a hand-constructed profile object.

The critical invariant is the regression guard: registering a profile makes
Autark a *known provider* in ``agent/model_metadata.py``, which SKIPS the generic
live ``/v1/models`` context probe. The profile hook must therefore supply the
window itself, or an unpinned client silently drops to the 256,000 fallback.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

PLUGIN_DIR = Path(__file__).resolve().parent.parent

CONTRACTS = (
    "autark-agent",
    "autark-pro",
    "autark-deep",
    "autark-agent-private",
    "autark-pro-private",
    "autark-deep-private",
)

EXPECTED_CONTEXT = 1_048_576


@pytest.fixture(scope="module")
def hermes_home(tmp_path_factory):
    """Install the plugin into a throwaway HERMES_HOME and import the registry."""
    home = tmp_path_factory.mktemp("hermes-autark")
    dest = home / "plugins" / "model-providers" / "autark"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PLUGIN_DIR, dest, ignore=shutil.ignore_patterns("tests", "__pycache__"))

    import os

    old = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = str(home)
    try:
        yield home
    finally:
        if old is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = old


@pytest.fixture(scope="module")
def profile(hermes_home):
    from providers import get_provider_profile

    prof = get_provider_profile("autark")
    assert prof is not None, "autark profile did not register"
    return prof


class TestIdentity:
    def test_registers_under_canonical_name(self, profile):
        assert profile.name == "autark"

    def test_alias_resolves(self, hermes_home):
        from providers import get_provider_profile

        assert get_provider_profile("autark-ai") is not None

    def test_base_url_and_hostname(self, profile):
        assert profile.base_url == "https://api.autark.ai/v1"
        assert profile.get_hostname() == "api.autark.ai"

    def test_uses_api_key_auth(self, profile):
        assert profile.auth_type == "api_key"
        assert "AUTARK_API_KEY" in profile.env_vars


class TestContextLength:
    def test_all_contracts_report_the_window(self, profile):
        for contract in CONTRACTS:
            assert profile.get_model_context_length(contract) == EXPECTED_CONTEXT

    def test_unknown_model_returns_none(self, profile):
        """An unrecognised id must fall through, not inherit a contract's window."""
        assert profile.get_model_context_length("some-other-model") is None

    def test_case_and_whitespace_tolerant(self, profile):
        assert profile.get_model_context_length("  AUTARK-Agent ") == EXPECTED_CONTEXT

    def test_empty_model_returns_none(self, profile):
        assert profile.get_model_context_length("") is None


class TestNoRegression:
    """The reason this profile overrides the hook at all."""

    def test_registering_makes_autark_a_known_provider(self, profile):
        """Documents WHY the override exists: this is what skips the live probe."""
        from agent import model_metadata as mm

        assert mm._is_known_provider_base_url(profile.base_url) is True

    def test_unpinned_resolution_is_not_the_fallback(self, profile):
        """A fresh install with no config pin must get 1M, not 256K."""
        from agent import model_metadata as mm

        for contract in CONTRACTS:
            ctx = mm.get_model_context_length(
                contract,
                base_url=profile.base_url,
                api_key="",
                config_context_length=None,
                provider="autark",
            )
            assert ctx == EXPECTED_CONTEXT, f"{contract} resolved to {ctx}"
            assert ctx != mm.DEFAULT_FALLBACK_CONTEXT


class TestCatalog:
    def test_fallback_models_cover_the_contract_surface(self, profile):
        assert set(profile.fallback_models) == set(CONTRACTS)

    def test_model_capabilities_match_the_hook(self, profile):
        for contract in CONTRACTS:
            caps = profile.model_capabilities[contract]
            assert caps["context_length"] == EXPECTED_CONTEXT

    def test_aux_model_is_a_real_contract(self, profile):
        assert profile.default_aux_model in CONTRACTS

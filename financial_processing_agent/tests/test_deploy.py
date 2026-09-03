"""Agent Engine resource-name helper (no live Vertex call)."""

import pytest

from deployment.deploy import normalize_engine_resource


def test_normalize_engine_resource_accepts_id_or_full_name():
    """Bare numeric ids must expand to reasoningEngines/, not a location suffix."""
    full = (
        "projects/light-operator-364723/locations/us-central1/"
        "reasoningEngines/5278317169568907264"
    )
    assert normalize_engine_resource(full) == full
    assert (
        normalize_engine_resource(
            "5278317169568907264",
            project="light-operator-364723",
            location="us-central1",
        )
        == full
    )
    assert (
        normalize_engine_resource(
            "reasoningEngines/5278317169568907264",
            project="light-operator-364723",
            location="us-central1",
        )
        == full
    )
    assert normalize_engine_resource('  "5278317169568907264"  ') == full


def test_normalize_engine_resource_rejects_display_name():
    """A display name is not a resource; deploy looks that up separately."""
    with pytest.raises(ValueError, match="reasoningEngines"):
        normalize_engine_resource("fpa831-agent-dev")


def test_normalize_engine_resource_empty():
    """Empty input means create (or display-name lookup) in apply()."""
    assert normalize_engine_resource("") == ""
    assert normalize_engine_resource("   ") == ""

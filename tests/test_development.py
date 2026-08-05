from pathlib import Path

import pytest

from docent.development import (
    DevelopmentError,
    derive_development_frontier,
    load_development_manifest,
    validate_development_manifest,
)

ROOT = Path(__file__).parents[1]


def test_development_manifests_validate_and_are_unique() -> None:
    manifest = load_development_manifest(ROOT)

    assert len({item.capability_id for item in manifest.capabilities}) == len(manifest.capabilities)
    assert len({item.pathway_id for item in manifest.pathways}) == len(manifest.pathways)


def test_current_capabilities_and_human_selection_are_honest() -> None:
    manifest = load_development_manifest(ROOT)
    capabilities = {item.capability_id: item for item in manifest.capabilities}
    experiments = {item.experiment_id: item for item in manifest.experiments}

    assert capabilities["bounded-single-user-chat"].status == "implemented"
    assert capabilities["shared-room-message-transport"].status == "partial"
    assert capabilities["mediated-room-runtime"].status == "absent"
    assert capabilities["external-runtime-adapter"].status == "absent"
    assert experiments["public-self-demo-2026-08"].result_status == "active"
    assert experiments["openrouter-live-inference-demo"].status == "active"
    assert experiments["openrouter-live-inference-demo"].result_status == "active"
    assert all(decision.decided_by == "human" for decision in manifest.decisions)


def test_frontier_derivation_is_deterministic_and_has_no_optimum() -> None:
    manifest = load_development_manifest(ROOT)

    first = derive_development_frontier(manifest)
    second = derive_development_frontier(manifest)

    assert first == second
    assert first.optimal_pathway is None
    assert first.human_selection_required is True
    assert first.selected_pathway_ids == [
        "openrouter-live-inference",
        "public-self-demo",
    ]
    assert [item.pathway.pathway_id for item in first.admissible_pathways] == sorted(
        item.pathway.pathway_id for item in first.admissible_pathways
    )
    blocked = {item.pathway.pathway_id: item for item in first.blocked_pathways}
    assert "external-runtime-adapter" in blocked
    assert blocked["external-runtime-adapter"].unsatisfied_preconditions


def test_duplicate_ids_are_rejected() -> None:
    manifest = load_development_manifest(ROOT)
    duplicate = manifest.model_copy(
        update={"capabilities": [*manifest.capabilities, manifest.capabilities[0]]}
    )

    with pytest.raises(DevelopmentError, match="duplicate capability IDs"):
        validate_development_manifest(duplicate, ROOT)


def test_capability_dependency_cycles_are_rejected() -> None:
    manifest = load_development_manifest(ROOT)
    capabilities = list(manifest.capabilities)
    first = capabilities[0].model_copy(update={"dependencies": [capabilities[1].capability_id]})
    second = capabilities[1].model_copy(update={"dependencies": [capabilities[0].capability_id]})
    cyclic = manifest.model_copy(update={"capabilities": [first, second, *capabilities[2:]]})

    with pytest.raises(DevelopmentError, match="capability dependency cycle"):
        validate_development_manifest(cyclic, ROOT)

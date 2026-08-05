from __future__ import annotations

from datetime import date
from pathlib import Path, PurePosixPath
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

CapabilityStatus = Literal["implemented", "partial", "experimental", "absent", "deprecated"]
PathwayStatus = Literal[
    "proposed",
    "available",
    "selected",
    "active",
    "demonstrated",
    "accepted",
    "blocked",
    "rejected",
    "superseded",
]
PressureLevel = Literal["low", "medium", "high", "unknown"]
EvidenceStatus = Literal["pending", "satisfied"]


class CapabilityRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str
    description: str
    status: CapabilityStatus
    evidence_basis: list[str]
    implementation_references: list[str]
    validation_references: list[str]
    limitations: list[str]
    dependencies: list[str]
    public: bool
    last_reviewed: date | str
    uncertainty_notes: list[str] = Field(default_factory=list)


class CapabilityRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    allowed_statuses: list[CapabilityStatus]


class PressureProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_visibility: PressureLevel
    immediate_usefulness: PressureLevel
    information_gain: PressureLevel
    engineering_cost: PressureLevel
    operational_cost: PressureLevel
    security_exposure: PressureLevel
    architectural_lock_in: PressureLevel
    reversibility: PressureLevel
    future_option_value: PressureLevel
    dependence_on_external_services: PressureLevel
    authors_note: str


class CompletionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    evidence_type: Literal["repository", "live"]
    description: str
    status: EvidenceStatus = "pending"
    reference: str | None = None


class PathwayRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pathway_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str
    intent: str
    status: PathwayStatus
    evidence_basis: list[str]
    preconditions: list[CapabilityRequirement]
    proposed_changes: list[str]
    capabilities_advanced: list[str]
    invariants: list[str]
    risks: list[str]
    unresolved_uncertainties: list[str]
    reversibility: str
    lock_in_implications: str
    completion_evidence: list[CompletionEvidence]
    implementation_references: list[str]
    pathways_unlocked: list[str]
    pathways_made_harder: list[str]
    decision_history: list[str]
    pressure_profile: PressureProfile
    public_explanation: str

    @model_validator(mode="after")
    def demonstrated_requires_evidence(self) -> PathwayRecord:
        if self.status in {"demonstrated", "accepted"} and any(
            item.status != "satisfied" for item in self.completion_evidence
        ):
            raise ValueError("demonstrated or accepted pathways require all completion evidence")
        return self


class DecisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    date: date
    status: Literal["proposed", "accepted", "superseded"]
    selected_pathway_id: str
    context: list[str]
    rationale: list[str]
    options_preserved: list[str]
    consequences: list[str]
    decided_by: Literal["human"]


class ExperimentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    title: str
    selected_pathway_id: str
    hypothesis: str
    status: Literal["pending", "active", "completed", "failed", "inconclusive"]
    setup: list[str]
    expected_observations: list[str]
    completion_evidence: list[str]
    failure_conditions: list[str]
    safety_boundaries: list[str]
    observations: list[str]
    result_status: Literal["pending", "active", "supported", "not-supported", "inconclusive"]

    @model_validator(mode="after")
    def active_is_not_success(self) -> ExperimentRecord:
        if self.status in {"pending", "active"} and self.result_status not in {
            "pending",
            "active",
        }:
            raise ValueError("an unfinished experiment cannot report a successful result")
        return self


class DevelopmentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capabilities: list[CapabilityRecord]
    pathways: list[PathwayRecord]
    decisions: list[DecisionRecord]
    experiments: list[ExperimentRecord]


class PathwayAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pathway: PathwayRecord
    admissible: bool
    unsatisfied_preconditions: list[str]


class DevelopmentFrontier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    implemented_capabilities: list[CapabilityRecord]
    partial_capabilities: list[CapabilityRecord]
    admissible_pathways: list[PathwayAssessment]
    blocked_pathways: list[PathwayAssessment]
    selected_pathway_ids: list[str]
    active_experiment_ids: list[str]
    human_selection_required: bool = True
    optimal_pathway: None = None
    explanation: str = (
        "Pressure profiles are authored qualitative descriptions. The project does not "
        "compute or claim an objectively optimal pathway; humans select pathways."
    )


class DevelopmentError(RuntimeError):
    pass


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise DevelopmentError(f"Expected a YAML object: {path}")
    return value


def _safe_reference(reference: str) -> bool:
    path = PurePosixPath(reference)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in reference


def load_development_manifest(root: Path) -> DevelopmentManifest:
    development_root = root / "development"
    capabilities_raw = _load_yaml(development_root / "capabilities.yaml")
    capabilities = [
        CapabilityRecord.model_validate(item) for item in capabilities_raw["capabilities"]
    ]
    pathways = [
        PathwayRecord.model_validate(_load_yaml(path))
        for path in sorted((development_root / "pathways").glob("*.yaml"))
    ]
    decisions = [
        DecisionRecord.model_validate(_load_yaml(path))
        for path in sorted((development_root / "decisions").glob("*.yaml"))
    ]
    experiments = [
        ExperimentRecord.model_validate(_load_yaml(path))
        for path in sorted((development_root / "experiments").glob("*.yaml"))
    ]
    manifest = DevelopmentManifest(
        capabilities=capabilities,
        pathways=pathways,
        decisions=decisions,
        experiments=experiments,
    )
    validate_development_manifest(manifest, root)
    return manifest


def _duplicates(values: list[str]) -> list[str]:
    return sorted({value for value in values if values.count(value) > 1})


def _dependency_cycles(capabilities: dict[str, CapabilityRecord]) -> list[list[str]]:
    cycles: list[list[str]] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(capability_id: str) -> None:
        if capability_id in visiting:
            start = visiting.index(capability_id)
            cycles.append(visiting[start:] + [capability_id])
            return
        if capability_id in visited:
            return
        visiting.append(capability_id)
        for dependency in capabilities[capability_id].dependencies:
            if dependency in capabilities:
                visit(dependency)
        visiting.pop()
        visited.add(capability_id)

    for capability_id in sorted(capabilities):
        visit(capability_id)
    return cycles


def validate_development_manifest(manifest: DevelopmentManifest, root: Path) -> None:
    errors: list[str] = []
    capability_ids = [item.capability_id for item in manifest.capabilities]
    pathway_ids = [item.pathway_id for item in manifest.pathways]
    decision_ids = [item.decision_id for item in manifest.decisions]
    experiment_ids = [item.experiment_id for item in manifest.experiments]
    check_evidence_files = (root / "tests").is_dir()
    for label, values in (
        ("capability", capability_ids),
        ("pathway", pathway_ids),
        ("decision", decision_ids),
        ("experiment", experiment_ids),
    ):
        if duplicates := _duplicates(values):
            errors.append(f"duplicate {label} IDs: {', '.join(duplicates)}")

    capabilities = {item.capability_id: item for item in manifest.capabilities}
    pathways = {item.pathway_id: item for item in manifest.pathways}
    for capability in manifest.capabilities:
        for dependency in capability.dependencies:
            if dependency not in capabilities:
                errors.append(f"{capability.capability_id}: unknown dependency {dependency}")
        for reference in capability.implementation_references + capability.validation_references:
            if not _safe_reference(reference):
                errors.append(f"{capability.capability_id}: unsafe reference {reference}")
            elif check_evidence_files and not (root / reference).exists():
                errors.append(f"{capability.capability_id}: missing evidence reference {reference}")

    for pathway in manifest.pathways:
        unsatisfied = []
        for requirement in pathway.preconditions:
            if requirement.capability_id not in capabilities:
                errors.append(
                    f"{pathway.pathway_id}: unknown capability {requirement.capability_id}"
                )
            elif capabilities[requirement.capability_id].status not in requirement.allowed_statuses:
                unsatisfied.append(requirement.capability_id)
        for capability_id in pathway.capabilities_advanced:
            if capability_id not in capabilities:
                errors.append(f"{pathway.pathway_id}: unknown advanced capability {capability_id}")
        for related in pathway.pathways_unlocked + pathway.pathways_made_harder:
            if related not in pathways:
                errors.append(f"{pathway.pathway_id}: unknown related pathway {related}")
        for reference in pathway.implementation_references:
            if not _safe_reference(reference):
                errors.append(f"{pathway.pathway_id}: unsafe reference {reference}")
        if pathway.status == "blocked" and not unsatisfied:
            errors.append(f"{pathway.pathway_id}: blocked pathway has no unsatisfied precondition")
        if pathway.status in {"available", "selected", "active"} and unsatisfied:
            errors.append(
                f"{pathway.pathway_id}: {pathway.status} pathway has unsatisfied preconditions: "
                + ", ".join(unsatisfied)
            )

    for decision in manifest.decisions:
        if decision.selected_pathway_id not in pathways:
            errors.append(f"{decision.decision_id}: unknown pathway {decision.selected_pathway_id}")
        for pathway_id in decision.options_preserved:
            if pathway_id not in pathways:
                errors.append(f"{decision.decision_id}: unknown preserved pathway {pathway_id}")
    for experiment in manifest.experiments:
        if experiment.selected_pathway_id not in pathways:
            errors.append(
                f"{experiment.experiment_id}: unknown pathway {experiment.selected_pathway_id}"
            )

    for cycle in _dependency_cycles(capabilities):
        errors.append(f"capability dependency cycle: {' -> '.join(cycle)}")
    if errors:
        raise DevelopmentError("Invalid development manifests:\n" + "\n".join(sorted(set(errors))))


def derive_development_frontier(manifest: DevelopmentManifest) -> DevelopmentFrontier:
    capabilities = {item.capability_id: item for item in manifest.capabilities}
    admissible: list[PathwayAssessment] = []
    blocked: list[PathwayAssessment] = []
    terminal = {"rejected", "superseded"}
    for pathway in sorted(manifest.pathways, key=lambda item: item.pathway_id):
        unsatisfied = [
            f"{requirement.capability_id} must be one of {', '.join(requirement.allowed_statuses)} "
            f"(currently {capabilities[requirement.capability_id].status})"
            for requirement in pathway.preconditions
            if capabilities[requirement.capability_id].status not in requirement.allowed_statuses
        ]
        assessment = PathwayAssessment(
            pathway=pathway,
            admissible=not unsatisfied and pathway.status not in terminal,
            unsatisfied_preconditions=unsatisfied,
        )
        (admissible if assessment.admissible else blocked).append(assessment)
    selected = sorted(
        {
            decision.selected_pathway_id
            for decision in manifest.decisions
            if decision.status == "accepted"
        }
    )
    return DevelopmentFrontier(
        implemented_capabilities=sorted(
            (item for item in manifest.capabilities if item.status == "implemented"),
            key=lambda item: item.capability_id,
        ),
        partial_capabilities=sorted(
            (item for item in manifest.capabilities if item.status in {"partial", "experimental"}),
            key=lambda item: item.capability_id,
        ),
        admissible_pathways=admissible,
        blocked_pathways=blocked,
        selected_pathway_ids=selected,
        active_experiment_ids=sorted(
            item.experiment_id for item in manifest.experiments if item.status == "active"
        ),
    )


def validate_main() -> None:
    manifest = load_development_manifest(Path.cwd())
    frontier = derive_development_frontier(manifest)
    print(
        f"Validated {len(manifest.capabilities)} capabilities, {len(manifest.pathways)} pathways, "
        f"{len(manifest.decisions)} decisions, and {len(manifest.experiments)} experiments; "
        f"{len(frontier.admissible_pathways)} pathways are currently admissible."
    )

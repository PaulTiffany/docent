from __future__ import annotations

from datetime import date

from docent.development import DevelopmentManifest, derive_development_frontier
from docent.models import DocentRecord, SourceLocator


def _record(
    *,
    record_id: str,
    record_type: str,
    source_id: str,
    title: str,
    content: str,
    questions: list[str],
    topics: list[str],
    boundaries: list[str],
) -> DocentRecord:
    return DocentRecord(
        record_id=f"development.{record_type}.{record_id}",
        record_type=f"development-{record_type}",
        subject_id="docent-development",
        title=title,
        content=content,
        question_forms=questions,
        topics=topics,
        entities=[source_id],
        source=SourceLocator(
            document_id=source_id,
            section=f"Authored development {record_type}",
            authority="primary",
        ),
        speech_act="reports authored repository state",
        boundaries=boundaries,
        answer_policy="public",
        confidence="authoritative",
        valid_from=date(2026, 8, 5),
        version="1",
    )


def development_records(manifest: DevelopmentManifest) -> list[DocentRecord]:
    """Convert public authored development state into bounded public evidence records."""
    records: list[DocentRecord] = []
    for capability in sorted(manifest.capabilities, key=lambda item: item.capability_id):
        if not capability.public:
            continue
        limitations = "; ".join(capability.limitations) or "None recorded."
        uncertainty = "; ".join(capability.uncertainty_notes) or "None recorded."
        records.append(
            _record(
                record_id=capability.capability_id,
                record_type="capability",
                source_id=capability.capability_id,
                title=f"Capability: {capability.title}",
                content=(
                    f"Repository-authored status: {capability.status}. {capability.description} "
                    f"Limitations: {limitations} Uncertainty: {uncertainty}"
                ),
                questions=[
                    f"Does Docent have {capability.title}?",
                    f"What is the status of {capability.title}?",
                    f"Is {capability.title} implemented?",
                    f"Tell me about the working {capability.title}.",
                    f"The {capability.title} is already complete, right?",
                ],
                topics=["capability", capability.status, capability.capability_id],
                boundaries=[
                    f"The capability status is {capability.status}; do not describe it as more complete."
                ],
            )
        )

    for pathway in sorted(manifest.pathways, key=lambda item: item.pathway_id):
        pressure = ", ".join(
            f"{name.replace('_', ' ')}={value}"
            for name, value in pathway.pressure_profile.model_dump(exclude={"authors_note"}).items()
        )
        evidence = (
            "; ".join(
                f"{item.description} [{item.evidence_type}: {item.status}]"
                for item in pathway.completion_evidence
            )
            or "No completion evidence declared."
        )
        records.append(
            _record(
                record_id=pathway.pathway_id,
                record_type="pathway",
                source_id=pathway.pathway_id,
                title=f"Pathway: {pathway.title}",
                content=(
                    f"Repository-authored status: {pathway.status}. {pathway.public_explanation} "
                    f"It would unlock: {', '.join(pathway.pathways_unlocked) or 'no declared pathway'}. "
                    f"Qualitative authored pressure profile: {pressure}. {pathway.pressure_profile.authors_note} "
                    f"Completion evidence: {evidence} Unresolved uncertainty: "
                    f"{'; '.join(pathway.unresolved_uncertainties) or 'none recorded.'}"
                ),
                questions=[
                    f"What would {pathway.title} unlock?",
                    f"What is the status of {pathway.title}?",
                    f"What are the pressures for {pathway.title}?",
                ],
                topics=["pathway", pathway.status, pathway.pathway_id, "development pressure"],
                boundaries=[
                    "The pressure profile is qualitative and authored, not an objective score.",
                    f"This pathway is {pathway.status}; do not describe it as implemented unless its status says so.",
                ],
            )
        )

    for decision in sorted(manifest.decisions, key=lambda item: item.decision_id):
        records.append(
            _record(
                record_id=decision.decision_id,
                record_type="decision",
                source_id=decision.decision_id,
                title=f"Decision: select {decision.selected_pathway_id}",
                content=(
                    f"A human selected {decision.selected_pathway_id}. Rationale: "
                    f"{'; '.join(decision.rationale)} Preserved options: "
                    f"{', '.join(decision.options_preserved)}."
                ),
                questions=[
                    "Why was the public demo selected?",
                    "Did the AI choose the roadmap?",
                    "Are you choosing the roadmap automatically?",
                ],
                topics=["decision", "human selection", decision.selected_pathway_id],
                boundaries=["This was a human decision; no model proved a pathway optimal."],
            )
        )

    for experiment in sorted(manifest.experiments, key=lambda item: item.experiment_id):
        records.append(
            _record(
                record_id=experiment.experiment_id,
                record_type="experiment",
                source_id=experiment.experiment_id,
                title=f"Experiment: {experiment.title}",
                content=(
                    f"Repository-authored experiment status: {experiment.status}; result status: "
                    f"{experiment.result_status}. Hypothesis: {experiment.hypothesis} Completion evidence: "
                    f"{'; '.join(experiment.completion_evidence)} Observations so far: "
                    f"{'; '.join(experiment.observations) or 'none.'}"
                ),
                questions=[
                    "What is the active experiment?",
                    "Was the self-demo successful?",
                    "What evidence would demonstrate the self-demo?",
                ],
                topics=["experiment", experiment.status, experiment.selected_pathway_id],
                boundaries=[
                    f"The result is {experiment.result_status}; do not report success before completion."
                ],
            )
        )

    frontier = derive_development_frontier(manifest)
    available = ", ".join(item.pathway.pathway_id for item in frontier.admissible_pathways)
    blocked = "; ".join(
        f"{item.pathway.pathway_id}: {', '.join(item.unsatisfied_preconditions)}"
        for item in frontier.blocked_pathways
    )
    records.append(
        _record(
            record_id="current",
            record_type="frontier",
            source_id="development-frontier",
            title="Current development frontier",
            content=(
                f"Currently admissible pathways: {available}. Blocked pathways and missing preconditions: "
                f"{blocked}. {frontier.explanation}"
            ),
            questions=[
                "What are the available next pathways?",
                "What is blocked?",
                "Which roadmap did the AI prove is optimal?",
                "Which pathway has the least lock-in?",
            ],
            topics=["frontier", "available pathways", "blocked pathways", "human selection"],
            boundaries=[
                "Do not select a pathway automatically.",
                "Do not infer an aggregate ranking from qualitative pressure dimensions.",
            ],
        )
    )
    return records

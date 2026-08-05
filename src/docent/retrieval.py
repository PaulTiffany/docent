from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from docent.models import DocentRecord, RetrievedRecord

_TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
_AUTHORITY_WEIGHT = {
    "primary": 1.15,
    "official": 1.08,
    "contextual": 1.0,
    "commentary": 0.92,
}
_CONFIDENCE_WEIGHT = {
    "authoritative": 1.10,
    "high": 1.06,
    "medium": 1.0,
    "low": 0.94,
    "unknown": 0.90,
}


def tokenize(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(text)]


@dataclass(frozen=True)
class IndexedRecord:
    record: DocentRecord
    term_counts: Counter[str]
    length: int


class LexicalRetriever:
    """Small deterministic BM25-style retriever with typed-record boosts."""

    def __init__(self, records: list[DocentRecord]) -> None:
        self.records = records
        self.index = [
            IndexedRecord(
                record=record,
                term_counts=Counter(tokenize(record.retrieval_text())),
                length=max(1, len(tokenize(record.retrieval_text()))),
            )
            for record in records
        ]
        self.avg_length = sum(item.length for item in self.index) / len(self.index)
        document_frequency: Counter[str] = Counter()
        for item in self.index:
            document_frequency.update(item.term_counts.keys())
        n = len(self.index)
        self.idf = {
            term: math.log(1 + (n - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def search(
        self, query: str, limit: int = 6, minimum_score: float = 0.0
    ) -> list[RetrievedRecord]:
        """Search records that are safe for a public response."""
        return self._search(query, limit=limit, minimum_score=minimum_score, public_only=True)

    def search_internal(
        self, query: str, limit: int = 6, minimum_score: float = 0.0
    ) -> list[RetrievedRecord]:
        """Explicitly search every record for a future trusted internal caller."""
        return self._search(query, limit=limit, minimum_score=minimum_score, public_only=False)

    def _search(
        self, query: str, *, limit: int, minimum_score: float, public_only: bool
    ) -> list[RetrievedRecord]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        query_counts = Counter(query_tokens)
        normalized_query = " ".join(query_tokens)
        results: list[RetrievedRecord] = []
        k1 = 1.5
        b = 0.75

        for item in self.index:
            if public_only and item.record.answer_policy != "public":
                continue
            score = 0.0
            reasons: list[str] = []
            for term, qtf in query_counts.items():
                tf = item.term_counts.get(term, 0)
                if not tf:
                    continue
                idf = self.idf.get(term, 0.0)
                denominator = tf + k1 * (1 - b + b * item.length / self.avg_length)
                score += idf * ((tf * (k1 + 1)) / denominator) * (1 + math.log(qtf))

            question_forms = [" ".join(tokenize(value)) for value in item.record.question_forms]
            if normalized_query in question_forms:
                score += 4.0
                reasons.append("exact question-form match")
            elif any(normalized_query and normalized_query in form for form in question_forms):
                score += 1.5
                reasons.append("partial question-form match")

            query_set = set(query_tokens)
            topic_set = set(tokenize(" ".join(item.record.topics)))
            entity_set = set(tokenize(" ".join(item.record.entities)))
            topic_overlap = query_set & topic_set
            entity_overlap = query_set & entity_set
            if topic_overlap:
                score += 0.35 * len(topic_overlap)
                reasons.append("topic overlap")
            if entity_overlap:
                score += 0.55 * len(entity_overlap)
                reasons.append("entity overlap")

            score *= _AUTHORITY_WEIGHT[item.record.source.authority]
            score *= _CONFIDENCE_WEIGHT[item.record.confidence]
            # Normalize to an intuitive bounded score without changing ordering.
            bounded_score = score / (score + 5.0) if score > 0 else 0.0
            if bounded_score >= minimum_score:
                if not reasons and bounded_score > 0:
                    reasons.append("lexical relevance")
                results.append(
                    RetrievedRecord(record=item.record, score=bounded_score, reasons=reasons)
                )

        results.sort(
            key=lambda result: (
                result.score,
                _AUTHORITY_WEIGHT[result.record.source.authority],
                result.record.record_id,
            ),
            reverse=True,
        )
        return results[:limit]

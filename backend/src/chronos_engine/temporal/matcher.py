"""Deterministic TemporalThread matching for the ChronOS Engine (Phase 3C).

Given a newly detected ``TemporalEvent``, answers one question: does it
belong to an existing ``TemporalThread``? The matcher is deliberately
conservative — a false connection is worse than no connection.

Evidence signals (all deterministic, all explainable):

A. Subject/topic overlap   Normalized token overlap between the event and
                           thread.subject/description. Stopwords are removed
                           and tokens lightly stemmed. Generic tokens count
                           very little; meaningful shared tokens are the only
                           signal that can open the door to a match.
B. Type compatibility      A small documented map of naturally related
                           temporal types (e.g. DECISION -> LIFE_EVENT).
                           Supports a match, never creates one.
C. Goal association        Current GoalDetector evidence that clearly refers
                           to a candidate thread's subject. Never duplicated
                           goal logic — only reads existing structured output.
D. Consistency / change    GOAL_CHANGE / DECISION_CHANGE / GOAL_CONFLICT /
                           STATEMENT_CONFLICT evidence whose text or memory
                           references relate to the candidate. Supports, but
                           cannot independently create a match.
E. Memory continuity       Explicit memory-id links already stored on a
                           candidate thread (origin/related) intersecting IDs
                           attached to the current interaction. No historical
                           memory scans: only IDs already present in evidence.

Hard rules enforced below:

- Supporting evidence alone can never fabricate a match: a match requires
  direct topical overlap or explicit memory continuity, plus a total score
  at or above MATCH_THRESHOLD.
- Ambiguity guard: when two or more candidates are comparably plausible
  (separation below AMBIGUITY_MARGIN) no match is returned.
- Confidence is an explainable evidence-weighted score in [0, MAX_CONFIDENCE],
  not a statistically calibrated probability.

No AI, no embeddings, no vector search, no storage access: candidates are
handed in by the caller through a ``BaseTemporalStore`` abstraction; this
component never creates threads and never persists anything.
"""

import re
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from chronos_engine.core.interfaces import BaseTemporalThreadMatcher
from chronos_engine.state.models import ConsistencyResult, GoalAnalysisResult
from chronos_engine.temporal.models import (
    ActiveTemporalContext,
    TemporalEvent,
    TemporalThread,
    TemporalThreadMatchResult,
    TemporalType,
)

# --- Calibration -------------------------------------------------------------
# Conservative on purpose: matching must earn trust before later phases rely
# on it. These values are implementation-defined, documented and tested — they
# are not claimed to be statistically calibrated.

MATCH_THRESHOLD = 0.50
AMBIGUITY_MARGIN = 0.15
CANDIDATE_FLOOR = 0.30
MAX_CONFIDENCE = 0.95

_TOPIC_BASE = 0.30          # >=1 meaningful shared token found in thread.subject
_TOPIC_EXTRA = 0.08         # each additional meaningful shared subject token
_DESCRIPTION_BASE = 0.22    # meaningful tokens found only in thread.description
_DESCRIPTION_EXTRA = 0.06
_TOPIC_CAP = 0.50           # topic overlap alone can never reach threshold
_GENERIC_ONLY_OVERLAP = 0.10
_SAME_TYPE_BONUS = 0.10
_GOAL_ASSOCIATION_BONUS = 0.15
_CONSISTENCY_BONUS = 0.15
_ORIGIN_CONTINUITY_BONUS = 0.35
_RELATED_MEMORY_BONUS = 0.20

# Phase 4G: bonus when the user explicitly selected a thread and the
# candidate matches it.  GATED: only applies when the candidate already
# has at least one grounded evidence signal (topic overlap, type compat,
# goal association, consistency, or memory continuity).  Alone, this
# bonus can never push a zero-evidence candidate past MATCH_THRESHOLD.
_ACTIVE_THREAD_CONTINUITY_BONUS = 0.30

_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "but", "if", "then", "so", "because",
        "as", "of", "at", "by", "for", "with", "about", "into", "to", "from",
        "in", "on", "off", "out", "over", "under", "up", "down", "again",
        "further", "once", "here", "there", "when", "where", "why", "how",
        "all", "any", "both", "each", "few", "more", "most", "other", "some",
        "such", "no", "nor", "not", "only", "own", "same", "than", "too",
        "very", "can", "will", "just", "should", "now", "i", "im", "ive",
        "ill", "id", "me", "my", "mine", "myself", "we", "our", "ours",
        "you", "your", "yours", "he", "him", "his", "she", "her", "hers",
        "it", "its", "they", "them", "their", "theirs", "this", "that",
        "these", "those", "am", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "having", "do", "does", "did",
        "doing", "would", "could", "might", "must", "shall", "what", "which",
        "who", "whom", "whether", "actually", "maybe", "perhaps", "really",
    }
)

# Tokens too common across unrelated life stories to act as meaningful
# evidence on their own ("Build ChronOS" vs "I built a shelf").
_GENERIC_TOKENS = frozenset(
    {
        "thing", "things", "stuff", "something", "anything", "nothing",
        "everything", "new", "old", "current", "recent", "last", "next",
        "first", "second", "good", "bad", "big", "small", "great", "nice",
        "make", "made", "want", "wanted", "need", "needed", "think",
        "thought", "know", "knew", "feel", "felt", "life", "time", "times",
        "day", "days", "way", "ways", "lot", "bit", "much", "many", "one",
        "two", "get", "got", "getting", "go", "going", "went", "gone",
        "come", "came", "coming", "take", "took", "taken", "put", "see",
        "saw", "seen", "look", "looked", "looking", "happen", "keep",
    }
)

# Small documented compatibility map (symmetric). Compatibility supports a
# match; it never creates one alone. Weights stay far below MATCH_THRESHOLD
# so compatible types without topical overlap can never match.
_TYPE_COMPATIBILITY: Dict[FrozenSet[TemporalType], float] = {
    # A considered decision often matures into a real-life event/milestone.
    frozenset({TemporalType.DECISION, TemporalType.LIFE_EVENT}): 0.25,
    frozenset({TemporalType.DECISION, TemporalType.MILESTONE}): 0.20,
    frozenset({TemporalType.DECISION, TemporalType.PROMISE}): 0.15,
    # Pursuing a goal can culminate in a milestone or become a lived event.
    frozenset({TemporalType.GOAL, TemporalType.MILESTONE}): 0.25,
    frozenset({TemporalType.GOAL, TemporalType.LIFE_EVENT}): 0.15,
    # Anticipated futures often arrive as real events or milestones.
    frozenset({TemporalType.FUTURE_EXPECTATION, TemporalType.LIFE_EVENT}): 0.20,
    frozenset({TemporalType.FUTURE_EXPECTATION, TemporalType.MILESTONE}): 0.15,
    frozenset({TemporalType.PREDICTION, TemporalType.LIFE_EVENT}): 0.15,
    # Fears and beliefs frequently sit underneath decisions about them.
    frozenset({TemporalType.FEAR, TemporalType.DECISION}): 0.20,
    frozenset({TemporalType.BELIEF, TemporalType.DECISION}): 0.15,
}

# Consistency/change categories that indicate an evolving story. Preference
# and identity conflicts describe stable traits rather than temporal stories,
# so they intentionally do not contribute.
_CHANGE_TYPES = {"GOAL_CHANGE", "GOAL_CONFLICT", "DECISION_CHANGE", "STATEMENT_CONFLICT"}

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def _stem(token: str) -> str:
    """Very light suffix stripping ('decisions'->'decision', 'leaving'->'leav').

    Deliberately naive and deterministic: no language models, no dictionaries.
    """
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _normalize(text: Optional[str]) -> Set[str]:
    """Lowercase, tokenize, drop stopwords/too-short tokens, light-stem."""
    if not text:
        return set()
    tokens: Set[str] = set()
    for raw in _TOKEN_RE.findall(text.lower()):
        if len(raw) < 3:
            continue
        stemmed = _stem(raw)
        if stemmed in _STOPWORDS or len(stemmed) < 3:
            continue
        tokens.add(stemmed)
    return tokens


def _split_meaningful(tokens: Set[str]) -> Tuple[Set[str], Set[str]]:
    meaningful = {t for t in tokens if t not in _GENERIC_TOKENS}
    return meaningful, tokens - meaningful


class _CandidateScore:
    """Per-candidate deterministic score with explainable signal lines."""

    __slots__ = ("thread", "score", "signals", "topic_overlap", "continuity",
                  "active_thread_applied")

    def __init__(
        self,
        thread: TemporalThread,
        score: float,
        signals: List[str],
        topic_overlap: float,
        continuity: float,
        active_thread_applied: bool = False,
    ) -> None:
        self.thread = thread
        self.score = score
        self.signals = signals
        self.topic_overlap = topic_overlap
        self.continuity = continuity
        self.active_thread_applied = active_thread_applied


def _thread_memory_ids(thread: TemporalThread) -> Set[str]:
    ids = set(thread.related_memory_ids)
    if thread.origin_memory_id:
        ids.add(thread.origin_memory_id)
    return ids


class TemporalThreadMatcher(BaseTemporalThreadMatcher):
    """Default deterministic implementation of BaseTemporalThreadMatcher."""

    async def match_threads(
        self,
        event: TemporalEvent,
        candidate_threads: List[TemporalThread],
        goal_analysis: Optional[GoalAnalysisResult] = None,
        consistency_result: Optional[ConsistencyResult] = None,
        active_temporal_context: Optional[ActiveTemporalContext] = None,
    ) -> TemporalThreadMatchResult:
        if not candidate_threads:
            return TemporalThreadMatchResult(
                attempted=True,
                matched=False,
                reason="No existing threads available to compare against.",
                ambiguous=False,
                candidate_count=0,
            )

        scored = [
            self._score_candidate(
                event, thread, goal_analysis, consistency_result,
                active_temporal_context,
            )
            for thread in candidate_threads
        ]
        # Deterministic order: score desc, then id asc for stable ties.
        scored.sort(key=lambda c: (-c.score, c.thread.id))

        best = scored[0]
        second = scored[1] if len(scored) > 1 else None

        confidence = round(min(MAX_CONFIDENCE, best.score), 2)

        if best.score < CANDIDATE_FLOOR:
            return TemporalThreadMatchResult(
                attempted=True,
                matched=False,
                confidence=confidence,
                reason=(
                    f"No sufficiently related thread "
                    f"(best score {best.score:.2f} below consideration floor)."
                ),
                signals=best.signals,
                ambiguous=False,
                candidate_count=len(scored),
            )

        if (
            second is not None
            and best.score - second.score < AMBIGUITY_MARGIN
            and second.score >= CANDIDATE_FLOOR
        ):
            return TemporalThreadMatchResult(
                attempted=True,
                matched=False,
                confidence=confidence,
                reason=(
                    f"Ambiguous: threads '{best.thread.id}' and '{second.thread.id}' "
                    f"are similarly plausible (scores {best.score:.2f} vs "
                    f"{second.score:.2f}); refusing to guess."
                ),
                signals=best.signals + second.signals,
                ambiguous=True,
                candidate_count=len(scored),
            )

        hard_gate_open = (
            best.topic_overlap > 0
            or best.continuity > 0
            or best.active_thread_applied
        )
        if best.score >= MATCH_THRESHOLD and hard_gate_open:
            separation = (
                "clear of runner-up"
                if second is None or best.score - second.score >= AMBIGUITY_MARGIN
                else "no close competitor above consideration floor"
            )
            return TemporalThreadMatchResult(
                attempted=True,
                matched=True,
                thread_id=best.thread.id,
                confidence=confidence,
                reason=(
                    f"Thread '{best.thread.id}' matches with sufficient evidence "
                    f"(score {best.score:.2f} >= {MATCH_THRESHOLD:.2f}, {separation})."
                ),
                signals=best.signals,
                ambiguous=False,
                candidate_count=len(scored),
                matched_thread=best.thread,
            )

        return TemporalThreadMatchResult(
            attempted=True,
            matched=False,
            confidence=confidence,
            reason=(
                f"Best candidate below reliability threshold "
                f"(score {best.score:.2f} < {MATCH_THRESHOLD:.2f}) "
                f"or lacks direct topical/continuity evidence."
            ),
            signals=best.signals,
            ambiguous=False,
            candidate_count=len(scored),
        )

    # -- scoring internals ----------------------------------------------------

    def _score_candidate(
        self,
        event: TemporalEvent,
        thread: TemporalThread,
        goal_analysis: Optional[GoalAnalysisResult],
        consistency_result: Optional[ConsistencyResult],
        active_temporal_context: Optional[ActiveTemporalContext] = None,
    ) -> _CandidateScore:
        signals: List[str] = []

        thread_memories = _thread_memory_ids(thread)

        # A. Subject/topic overlap. Subject hits weigh most; description-only
        # hits count less (a shared word buried in prose is weaker evidence
        # than a shared subject).
        event_tokens = _normalize(event.description)
        subject_tokens = _normalize(thread.subject)
        description_tokens = _normalize(thread.description)
        thread_tokens = subject_tokens | description_tokens

        subject_shared = event_tokens & subject_tokens
        desc_only_shared = (event_tokens & description_tokens) - subject_shared

        topic_overlap = 0.0
        meaningful_subject, generic_subject = _split_meaningful(subject_shared)
        if meaningful_subject:
            topic_overlap = min(
                _TOPIC_CAP,
                _TOPIC_BASE + _TOPIC_EXTRA * (len(meaningful_subject) - 1),
            )
            detail = ", ".join(sorted(meaningful_subject))
            extras: List[str] = []
            if generic_subject:
                extras.append(f"generic: {', '.join(sorted(generic_subject))}")
            if desc_only_shared:
                extras.append(f"description: {', '.join(sorted(desc_only_shared))}")
            if extras:
                detail += f" ({'; '.join(extras)})"
            signals.append(f"Subject/topic overlap: {detail}.")
        else:
            meaningful_desc, _generic_desc = _split_meaningful(desc_only_shared)
            if meaningful_desc:
                topic_overlap = min(
                    _TOPIC_CAP,
                    _DESCRIPTION_BASE + _DESCRIPTION_EXTRA * (len(meaningful_desc) - 1),
                )
                signals.append(
                    f"Weak topic overlap (description only): "
                    f"{', '.join(sorted(meaningful_desc))}."
                )
            elif subject_shared or desc_only_shared:
                topic_overlap = _GENERIC_ONLY_OVERLAP
                shared_all = subject_shared | desc_only_shared
                signals.append(
                    f"Weak overlap, generic tokens only: {', '.join(sorted(shared_all))}."
                )

        # B. Temporal type compatibility.
        type_bonus = 0.0
        if thread.temporal_type and event.temporal_type:
            pair = frozenset({thread.temporal_type, event.temporal_type})
            if thread.temporal_type == event.temporal_type:
                type_bonus = _SAME_TYPE_BONUS
                signals.append(f"Same temporal type ({event.temporal_type.value}).")
            elif pair in _TYPE_COMPATIBILITY:
                type_bonus = _TYPE_COMPATIBILITY[pair]
                signals.append(
                    f"Compatible temporal types "
                    f"({thread.temporal_type.value} <-> {event.temporal_type.value})."
                )

        # C. Goal association from existing GoalDetector evidence.
        goal_bonus = 0.0
        goal_texts: List[str] = []
        if goal_analysis is not None:
            if goal_analysis.goal:
                goal_texts.append(goal_analysis.goal)
            if goal_analysis.matched_existing_goal and (
                not goal_analysis.goal
                or goal_analysis.matched_existing_goal != goal_analysis.goal
            ):
                goal_texts.append(goal_analysis.matched_existing_goal)
        for goal_text in goal_texts:
            shared_goal = _split_meaningful(_normalize(goal_text) & thread_tokens)[0]
            if shared_goal:
                goal_bonus = max(goal_bonus, _GOAL_ASSOCIATION_BONUS)
                snippet = goal_text if len(goal_text) <= 60 else goal_text[:57] + "..."
                signals.append(f"Goal association: current goal relates to thread ({snippet}).")
                break

        consistency_memory_ids: Set[str] = set()
        change_entries = []
        if consistency_result is not None:
            change_entries = [
                entry
                for entry in list(consistency_result.changes)
                + list(consistency_result.contradictions)
                if entry.type in _CHANGE_TYPES
            ]
            consistency_memory_ids.update(consistency_result.supporting_memory_ids)
            for entry in change_entries:
                consistency_memory_ids.update(entry.supporting_memory_ids)

        # E. Memory continuity (explicit links only — never a history scan).
        continuity = 0.0
        if event.memory_id and event.memory_id in thread_memories:
            continuity = max(continuity, _ORIGIN_CONTINUITY_BONUS)
            signals.append("Memory continuity: event memory already linked to this thread.")
        elif consistency_memory_ids & thread_memories:
            continuity = max(continuity, _RELATED_MEMORY_BONUS)
            signals.append("Memory continuity via consistency-evidence memories.")

        # D. Consistency / change evidence related to this specific thread.
        consistency_bonus = 0.0
        for entry in change_entries:
            entry_text = " ".join(
                part for part in (entry.description, entry.previous_value, entry.current_value) if part
            )
            related_by_text = bool(
                _split_meaningful(_normalize(entry_text) & thread_tokens)[0]
            )
            related_by_memory = bool(set(entry.supporting_memory_ids) & thread_memories)
            if related_by_text or related_by_memory:
                consistency_bonus = _CONSISTENCY_BONUS
                label = (entry.type or "change").lower().replace("_", " ")
                signals.append(f"Consistency/change evidence relates to thread ({label}).")
                break

        # Phase 4G: Active thread continuity. When the user explicitly
        # selected a thread and this candidate IS that thread, a moderate
        # bonus is applied — but ONLY when the candidate already has a
        # topical or memory connection (topic_overlap > 0 or continuity > 0).
        # Alone, the selection can never push a zero-evidence candidate
        # past the match threshold.
        active_thread_bonus = 0.0
        _active_thread_applied = False
        if (
            active_temporal_context is not None
            and active_temporal_context.thread_id == thread.id
        ):
            has_grounded_evidence = (
                topic_overlap > 0
                or continuity > 0
            )
            if has_grounded_evidence:
                active_thread_bonus = _ACTIVE_THREAD_CONTINUITY_BONUS
                _active_thread_applied = True
                signals.append(
                    "Active thread selection: user explicitly continuing this story."
                )

        total = round(
            min(1.0, topic_overlap + type_bonus + goal_bonus + consistency_bonus
                + continuity + active_thread_bonus),
            4,
        )
        return _CandidateScore(
            thread, total, signals, topic_overlap, continuity,
            active_thread_applied=_active_thread_applied,
        )


__all__ = ["TemporalThreadMatcher"]

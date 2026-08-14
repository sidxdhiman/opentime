"""Deterministic, offline consistency / continuity engine for ChronOS.

Scope
-----
The ConsistencyEngine compares the current input against what ChronOS already
knows about the user (identity goals & preferences, previously stored memories)
and reports meaningful differences:

* ``GOAL_CHANGE``       — an existing goal was abandoned or changed direction.
* ``GOAL_CONFLICT``     — the input conflicts with an active goal without
                          abandoning it (e.g. "spending my car savings" vs a
                          "save money for a car" goal).
* ``DECISION_CHANGE``   — a previously stated decision was reversed.
* ``PREFERENCE_CONFLICT`` — an established preference is being persistently
                          reversed (a single context-specific request is not
                          a conflict).
* ``STATEMENT_CONFLICT`` — the user states opposite facts/stances at different
                          times on the same topic.
* ``IDENTITY_CONFLICT``  — the input rejects a stored identity value.

A detected difference is **never** an accusation that the user is wrong. It is
a continuity signal: *the current state differs from previously stored state*.
The engine reports it so later layers can build on it.

No AI, no network, no ML, no full-database scan — the engine only reads the
context ChronOS retrieval already produced (relevant memories, identity,
goal analysis).
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from chronos_engine.core.interfaces import BaseConsistencyEngine
from chronos_engine.core.models import IdentityProfile, MemoryItem, RetrievedContext, UserInput
from chronos_engine.state.models import (
    ConsistencyResult,
    ContradictionResult,
    GoalAnalysisResult,
    GoalStatus,
)

# ---------------------------------------------------------------------------
# Goal-change detection (highest priority)
# ---------------------------------------------------------------------------

# GoalAnalysisResult statuses that represent a meaningful change from stored
# state. Ordinary progress / activity never triggers this.
CHANGE_STATUSES: Set[GoalStatus] = {GoalStatus.ABANDONED, GoalStatus.CHANGED}

# ---------------------------------------------------------------------------
# Goal-conflict detection
# ---------------------------------------------------------------------------

CONFLICT_WORDS: Tuple[str, ...] = (
    "spend", "spending", "spent", "waste", "wasting", "blow", "blowing",
    "ignore", "ignoring", "against", "contrary", "violate", "violates",
    "drop", "dropping", "forget", "sell", "give up on", "canceling",
    "cancelling", "put on hold", "put on pause",
)

# ---------------------------------------------------------------------------
# Decision-change detection
# ---------------------------------------------------------------------------

DECISION_MARKER = re.compile(
    r"\b(?:decided to|decide to|i('m| am|'ve| have)? going with|going with|"
    r"choose|picking|switch to|switching to|moving to|move to|adopt|"
    r"stick with|settle on|settled on)\s+(?:use\s+|using\s+|to use\s+)?"
    r"(?P<object>[\w.\-+]{2,})",
    re.IGNORECASE,
)

# Small deterministic domain buckets so decision objects are only compared when
# they belong to the same domain ("PostgreSQL" vs "MongoDB" are both databases).
DECISION_DOMAINS: Dict[str, Set[str]] = {
    "database": {"postgresql", "postgres", "mongodb", "mysql", "sqlite", "redis", "oracle", "dynamodb", "mariadb"},
    "language": {"python", "rust", "java", "javascript", "typescript", "go", "c++", "c#", "ruby", "kotlin"},
    "framework": {"react", "nextjs", "vue", "angular", "django", "fastapi", "flask", "spring"},
    "infrastructure": {"docker", "kubernetes", "aws", "gcp", "azure", "terraform"},
}

DECISION_OBJECTS: Dict[str, Set[str]] = {}
for _domain, _objects in DECISION_DOMAINS.items():
    for _obj in _objects:
        DECISION_OBJECTS[_obj] = {_domain}

# ---------------------------------------------------------------------------
# Preference-conflict detection
# ---------------------------------------------------------------------------

PERSISTENT_PREFERENCE = (
    "from now on", "going forward", "moving forward", "from now onwards",
    "always", "never", "in general", "i prefer", "i like my", "i want everything",
    "from now on i want", "i have always", "i decided i prefer",
)

# A single context-specific request ("give me a detailed explanation") is NOT a
# persistent preference change; only inputs carrying a persistent marker are.
# Distinguish these so a one-off request is never turned into a stored change.

CONCISE_WORDS = ("concise", "short", "brief", "summary", "quick", "tl;dr")
DETAILED_WORDS = ("detailed", "long", "in-depth", "in depth", "thorough",
                  "comprehensive", "elaborate", "full")

# ---------------------------------------------------------------------------
# Statement-conflict detection
# ---------------------------------------------------------------------------

NEGATIVE_STANCE = (
    "don't want", "do not want", "don't like", "do not like", "hate",
    "avoid", "not interested", "can't stand", "refuse", "won't work with",
    "don't want to work with", "do not want to work with", "no longer",
)

POSITIVE_STANCE = (
    "want to", "would like", "love", "like", "focus on", "interested in",
    "prefer", "enjoy", "want to work with", "now the language", "my favorite",
)

# ---------------------------------------------------------------------------
# Identity-conflict detection
# ---------------------------------------------------------------------------

NEGATION_MARKERS = (
    "don't", "do not", "never", "hate", "against", "not interested",
    "can't stand", "don't care", "don't believe",
)

_TOKENS_RE = re.compile(r"[a-z0-9]+")

STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "at", "for",
    "with", "by", "i", "my", "me", "we", "our", "you", "your", "it", "its",
    "is", "are", "was", "were", "be", "been", "am", "than", "that", "this",
    "these", "those", "so", "as", "but", "not", "no", "do", "does", "did",
    "if", "from", "about", "into", "over", "up", "down", "all", "will",
    "would", "can", "could", "should", "have", "has", "had", "they", "them",
    "their", "he", "she", "him", "her", "just", "also", "more", "most",
    "there", "really", "very", "too",
}


class ConsistencyEngine(BaseConsistencyEngine):
    """Compares the current input against stored context for continuity.

    Deterministic and fully offline. Reads only the context produced by
    ChronOS retrieval plus the identity profile — no unrestricted scans.
    """

    async def check_consistency(
        self,
        user_input: UserInput,
        retrieved_context: RetrievedContext,
        goal_analysis: Optional[GoalAnalysisResult] = None,
        identity: Optional[IdentityProfile] = None,
        current_memory_id: Optional[str] = None,
    ) -> ConsistencyResult:
        content = user_input.content or ""
        text = content.lower()

        contradictions: List[ContradictionResult] = []
        changes: List[ContradictionResult] = []

        self._check_goal_changes(goal_analysis, retrieved_context, current_memory_id, changes)
        self._check_goal_conflicts(text, goal_analysis, identity, retrieved_context, contradictions)
        self._check_decision_changes(text, retrieved_context, current_memory_id, contradictions)
        self._check_preference_conflicts(text, identity, retrieved_context, contradictions)
        self._check_statement_conflicts(text, retrieved_context, contradictions)
        self._check_identity_conflicts(text, identity, contradictions)

        supporting_ids: List[str] = []
        for event in contradictions + changes:
            for mid in event.supporting_memory_ids:
                if mid and mid not in supporting_ids:
                    supporting_ids.append(mid)

        if contradictions or changes:
            confidence = round(
                min(0.95, max(0.5, max(e.confidence for e in contradictions + changes))),
                2,
            )
        else:
            # No events: how confident can we be that the input is consistent?
            # Only as confident as the amount of stored context we compared it
            # against.
            context_amount = self._context_amount(identity, retrieved_context)
            if context_amount == 0:
                confidence = 0.2
            else:
                confidence = round(min(0.95, 0.55 + 0.04 * min(context_amount, 10)), 2)

        return ConsistencyResult(
            is_consistent=len(contradictions) == 0,
            confidence=confidence,
            contradictions=contradictions,
            changes=changes,
            supporting_memory_ids=supporting_ids,
        )

    # ------------------------------------------------------------------
    # Goal changes
    # ------------------------------------------------------------------

    def _check_goal_changes(
        self,
        goal_analysis: Optional[GoalAnalysisResult],
        retrieved_context: RetrievedContext,
        current_memory_id: Optional[str],
        changes: List[ContradictionResult],
    ) -> None:
        if goal_analysis is None:
            return

        # For a CHANGED goal, the new direction is usually also reported as a
        # NEW goal item — use it as the "into" side of the change.
        new_direction: Optional[str] = next(
            (
                item.goal
                for item in goal_analysis.items
                if item.status == GoalStatus.NEW and item.goal
            ),
            None,
        )

        for item in goal_analysis.items:
            if item.status not in CHANGE_STATUSES:
                continue
            goal = item.matched_existing_goal or item.goal
            if not goal:
                continue

            if item.status == GoalStatus.ABANDONED:
                current_value = f"Stopped pursuing: {goal}"
                description = (
                    "The current input indicates the previously stored goal "
                    f"'{goal}' is being abandoned."
                )
            else:
                current_value = new_direction or f"Changed direction from: {goal}"
                description = (
                    "The current input indicates the previously stored goal "
                    f"'{goal}' has changed direction."
                )

            supporting = self._memories_for_topic(goal, retrieved_context.relevant_memories)
            if current_memory_id:
                supporting.append(current_memory_id)

            confidence = round(
                min(
                    0.95,
                    0.35 + 0.45 * item.confidence + (0.20 if supporting else 0.0),
                ),
                2,
            )
            changes.append(
                ContradictionResult(
                    type="GOAL_CHANGE",
                    description=description,
                    previous_value=goal,
                    current_value=current_value,
                    confidence=confidence,
                    supporting_memory_ids=supporting,
                )
            )

    # ------------------------------------------------------------------
    # Goal conflicts
    # ------------------------------------------------------------------

    def _check_goal_conflicts(
        self,
        text: str,
        goal_analysis: Optional[GoalAnalysisResult],
        identity: Optional[IdentityProfile],
        retrieved_context: RetrievedContext,
        contradictions: List[ContradictionResult],
    ) -> None:
        goals = self._identity_goals(identity, retrieved_context)
        changed_or_abandoned = self._change_goal_set(goal_analysis)

        for goal in goals:
            if not goal or goal in changed_or_abandoned:
                continue
            if not self._topic_linked(text, goal):
                continue
            if not any(word in text for word in CONFLICT_WORDS):
                continue

            supporting = self._memories_for_topic(goal, retrieved_context.relevant_memories)
            confidence = round(min(0.85, 0.45 + 0.10 * len(supporting) + 0.10), 2)
            contradictions.append(
                ContradictionResult(
                    type="GOAL_CONFLICT",
                    description=(
                        f"The current input appears to conflict with the stored "
                        f"goal '{goal}' without abandoning it."
                    ),
                    previous_value=goal,
                    current_value=self._snippet(text),
                    confidence=confidence,
                    supporting_memory_ids=supporting,
                )
            )

    # ------------------------------------------------------------------
    # Decision changes
    # ------------------------------------------------------------------

    def _check_decision_changes(
        self,
        text: str,
        retrieved_context: RetrievedContext,
        current_memory_id: Optional[str],
        contradictions: List[ContradictionResult],
    ) -> None:
        current_object, current_domain = self._extract_decision(text)
        if not current_object or not current_domain:
            return

        for memory in retrieved_context.relevant_memories:
            previous_object, previous_domain = self._extract_decision(memory.content)
            if not previous_object or previous_domain != current_domain:
                continue
            if previous_object == current_object:
                continue

            supporting = [memory.id]
            if current_memory_id:
                supporting.append(current_memory_id)
            contradictions.append(
                ContradictionResult(
                    type="DECISION_CHANGE",
                    description=(
                        f"The current input reverses a previously stated "
                        f"{current_domain} decision: '{previous_object}' -> "
                        f"'{current_object}'."
                    ),
                    previous_value=previous_object,
                    current_value=current_object,
                    confidence=round(min(0.9, 0.55 + 0.15 * len(supporting)), 2),
                    supporting_memory_ids=supporting,
                )
            )

    # ------------------------------------------------------------------
    # Preference conflicts
    # ------------------------------------------------------------------

    def _check_preference_conflicts(
        self,
        text: str,
        identity: Optional[IdentityProfile],
        retrieved_context: RetrievedContext,
        contradictions: List[ContradictionResult],
    ) -> None:
        # A persistent marker ("from now on") signals a stored preference
        # change. Without one, this is at most a context-specific request and
        # must not be classified as a preference change.
        if not any(marker in text for marker in PERSISTENT_PREFERENCE):
            return

        current_polarity = self._preference_polarity(text)
        if current_polarity is None:
            return

        previous_polarity, previous_text = self._previous_preference(identity, retrieved_context)
        if previous_polarity is None or previous_polarity == current_polarity:
            return

        supporting = self._memories_with_polarity(previous_polarity, retrieved_context.relevant_memories)
        contradictions.append(
            ContradictionResult(
                type="PREFERENCE_CONFLICT",
                description=(
                    "The current input persistently reverses a previously stored "
                    f"preference ({previous_polarity} -> {current_polarity})."
                ),
                previous_value=previous_text or f"prefers {previous_polarity} responses",
                current_value=self._snippet(text),
                confidence=round(min(0.9, 0.6 + 0.10 * len(supporting)), 2),
                supporting_memory_ids=supporting,
            )
        )

    # ------------------------------------------------------------------
    # Statement conflicts
    # ------------------------------------------------------------------

    def _check_statement_conflicts(
        self,
        text: str,
        retrieved_context: RetrievedContext,
        contradictions: List[ContradictionResult],
    ) -> None:
        current_positive = any(marker in text for marker in POSITIVE_STANCE)
        current_negative = any(marker in text for marker in NEGATIVE_STANCE)
        if current_positive == current_negative:
            return

        input_tokens = set(self._meaningful(self._tokens(text)))
        for memory in retrieved_context.relevant_memories:
            mem_text = memory.content.lower()
            memory_positive = any(marker in mem_text for marker in POSITIVE_STANCE)
            memory_negative = any(marker in mem_text for marker in NEGATIVE_STANCE)

            topics = input_tokens & set(self._meaningful(self._tokens(mem_text)))
            if not topics:
                continue
            if (current_positive and memory_negative) or (current_negative and memory_positive):
                contradictions.append(
                    ContradictionResult(
                        type="STATEMENT_CONFLICT",
                        description=(
                            "The current input states an opposite stance on "
                            "the same topic as a previously stored statement."
                        ),
                        previous_value=self._snippet(memory.content),
                        current_value=self._snippet(text),
                        confidence=round(min(0.9, 0.65 + 0.05 * len(topics)), 2),
                        supporting_memory_ids=[memory.id],
                    )
                )

    # ------------------------------------------------------------------
    # Identity conflicts
    # ------------------------------------------------------------------

    def _check_identity_conflicts(
        self,
        text: str,
        identity: Optional[IdentityProfile],
        contradictions: List[ContradictionResult],
    ) -> None:
        if not identity or not any(marker in text for marker in NEGATION_MARKERS):
            return
        for value in identity.values:
            tokens = self._meaningful(self._tokens(value))
            if not tokens:
                continue
            if any(token in text for token in tokens):
                contradictions.append(
                    ContradictionResult(
                        type="IDENTITY_CONFLICT",
                        description=(
                            f"The current input appears to reject a stored "
                            f"identity value ('{value}')."
                        ),
                        previous_value=value,
                        current_value=self._snippet(text),
                        confidence=round(min(0.8, 0.55 + 0.05 * len(tokens)), 2),
                        supporting_memory_ids=[],
                    )
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokens(s: str) -> List[str]:
        return _TOKENS_RE.findall(s.lower())

    @classmethod
    def _meaningful(cls, words: List[str]) -> List[str]:
        return [w for w in words if w not in STOPWORDS]

    @classmethod
    def _snippet(cls, text: str, limit: int = 60) -> str:
        cleaned = " ".join(text.split())
        return cleaned[:limit] + ("..." if len(cleaned) > limit else "")

    def _identity_goals(
        self, identity: Optional[IdentityProfile], retrieved_context: RetrievedContext
    ) -> List[str]:
        if identity is not None:
            return list(identity.goals)
        return list(retrieved_context.identity_summary.get("goals", []))

    def _change_goal_set(self, goal_analysis: Optional[GoalAnalysisResult]) -> Set[str]:
        if goal_analysis is None:
            return set()
        return {
            item.matched_existing_goal or item.goal
            for item in goal_analysis.items
            if item.status in CHANGE_STATUSES and (item.matched_existing_goal or item.goal)
        }

    def _topic_linked(self, text: str, goal: str) -> bool:
        goal_tokens = self._meaningful(self._tokens(goal))
        input_tokens = set(self._meaningful(self._tokens(text)))
        if not goal_tokens:
            return False
        return any(token in input_tokens for token in goal_tokens)

    def _memories_for_topic(self, topic: str, memories: List[MemoryItem]) -> List[str]:
        topic_tokens = self._meaningful(self._tokens(topic))
        ids: List[str] = []
        for memory in memories:
            memory_tokens = set(self._meaningful(self._tokens(memory.content)))
            if memory_tokens and any(token in memory_tokens for token in topic_tokens):
                ids.append(memory.id)
        return ids

    @classmethod
    def _extract_decision(cls, text: str) -> Tuple[Optional[str], Optional[str]]:
        lower = (text or "").lower()
        match = DECISION_MARKER.search(lower)
        if not match:
            return None, None
        obj = match.group("object").strip(".,;:!?()")
        domain = DECISION_OBJECTS.get(obj)
        if domain:
            return obj, next(iter(domain))
        return None, None

    @classmethod
    def _preference_polarity(cls, text: str) -> Optional[str]:
        lower = text.lower()
        concise = any(word in lower for word in CONCISE_WORDS)
        detailed = any(word in lower for word in DETAILED_WORDS)
        if concise and not detailed:
            return "concise"
        if detailed and not concise:
            return "detailed"
        return None

    def _previous_preference(
        self, identity: Optional[IdentityProfile], retrieved_context: RetrievedContext
    ) -> Tuple[Optional[str], Optional[str]]:
        if identity is not None:
            for raw in identity.preferences.values():
                text = str(raw)
                polarity = self._preference_polarity(text)
                if polarity:
                    return polarity, self._snippet(text)
        for memory in retrieved_context.relevant_memories:
            polarity = self._preference_polarity(memory.content)
            if polarity:
                return polarity, self._snippet(memory.content)
        return None, None

    def _memories_with_polarity(
        self, polarity: str, memories: List[MemoryItem]
    ) -> List[str]:
        return [
            memory.id
            for memory in memories
            if self._preference_polarity(memory.content) == polarity
        ]

    @staticmethod
    def _context_amount(
        identity: Optional[IdentityProfile], retrieved_context: RetrievedContext
    ) -> int:
        amount = len(retrieved_context.relevant_memories)
        if identity is not None:
            amount += len(identity.goals) + len(identity.preferences) + len(identity.values)
        else:
            amount += len(retrieved_context.identity_summary.get("goals", []))
        return amount

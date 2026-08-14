"""Deterministic, offline goal detection for the ChronOS engine.

Scope
-----
The detector answers one question about the current input: *how does it relate
to the user's goals?* It decides whether the input:

* introduces a genuinely new goal (``NEW``),
* discusses an existing goal (``ACTIVE``),
* reports progress on an existing goal (``PROGRESS``),
* completes an existing goal (``COMPLETED``),
* abandons an existing goal (``ABANDONED``),
* is blocked from progressing on an existing goal (``BLOCKED``),
* signals that an existing goal has changed direction (``CHANGED``), or
* is unrelated to goals (``NONE``).

This is entirely deterministic — no LLM, no network, no ML. It is deliberately
conservative: a goal is never fabricated, and a trivial desire ("I want a
coffee") is not promoted to a persistent personal goal without strong
goal-introduction evidence.

Goals vs tasks
--------------
The detector may associate an input with an existing goal (e.g. "I finished
implementing the UserStateDetector" -> progress on "Build ChronOS") via
deterministic topic/domain association, but it will not turn an isolated task
("fix the login button") into a new long-term goal unless the input clearly
signals one.

Interface conventions follow the rest of ChronOS: async methods and a typed
``GoalAnalysisResult`` model shared in ``chronos_engine.state.models``.
"""

import re
from typing import Dict, List, Optional, Tuple

from chronos_engine.core.interfaces import BaseGoalDetector
from chronos_engine.core.models import UserInput
from chronos_engine.state.models import GoalAnalysisItem, GoalAnalysisResult, GoalStatus

# (substring pattern, weight, human-readable description)
Signal = Tuple[str, float, str]

# ---------------------------------------------------------------------------
# NEW-goal detection
# ---------------------------------------------------------------------------

NEW_GOAL_SIGNALS: List[Signal] = [
    ("my goal is to", 0.70, "explicit goal statement"),
    ("my goal is", 0.60, "explicit goal statement"),
    ("goal is", 0.50, "explicit goal statement"),
    ("i want to", 0.50, "goal intention language"),
    ("i'd like to", 0.40, "goal intention language"),
    ("i would like to", 0.40, "goal intention language"),
    ("i plan to", 0.50, "goal intention language"),
    ("plan to", 0.40, "goal intention language"),
    ("i'm working toward", 0.50, "goal pursuit language"),
    ("i am working toward", 0.50, "goal pursuit language"),
    ("working toward", 0.40, "goal pursuit language"),
    ("i'm trying to", 0.30, "goal pursuit language"),
    ("i need to", 0.20, "weak goal intention"),
    ("i've decided to", 0.50, "goal intention language"),
    ("i have decided to", 0.50, "goal intention language"),
    ("hope to", 0.40, "goal aspiration language"),
    ("aspiring to", 0.50, "goal aspiration language"),
    ("my focus is", 0.40, "goal focus language"),
]

# Verbs that strongly imply a long-lasting personal goal when they follow an
# intention phrase. Transient, everyday verbs are excluded on purpose.
GOAL_VERBS: set = {
    "learn", "create", "build", "make", "become", "master", "improve",
    "develop", "design", "write", "start", "launch", "complete", "achieve",
    "grow", "pass", "establish", "refine", "study", "break", "finish",
}

# Strong new-goal evidence threshold. Below this, an intention phrase alone is
# not enough to mint a persistent goal.
NEW_STRONG_THRESHOLD: float = 0.5
# Minimum score, combined with a strong goal verb, to call something a NEW goal.
NEW_WITH_VERB_THRESHOLD: float = 0.35

# Concrete-object desires are not goals. "I want a coffee" / "I need a nap".
TRIVIAL_DESIRE = re.compile(r"\b(want|need|would like|like) (a|an|the|my|some|one|another)\b")

# ---------------------------------------------------------------------------
# Existing-goal status language
# ---------------------------------------------------------------------------

CHANGED_SIGNALS: List[Signal] = [
    ("decided to focus on", 0.50, "direction change language"),
    ("changed my mind", 0.50, "direction change language"),
    ("shifted to", 0.40, "direction change language"),
    ("shifting to", 0.40, "direction change language"),
    ("instead", 0.30, "direction change language"),
    ("rather than", 0.40, "direction change language"),
    ("instead of", 0.30, "direction change language"),
    ("reprioritized", 0.45, "direction change language"),
    ("new direction", 0.45, "direction change language"),
    ("originally wanted", 0.50, "direction change language"),
]

ABANDONED_SIGNALS: List[Signal] = [
    ("don't want to", 0.40, "abandonment language"),
    ("do not want to", 0.40, "abandonment language"),
    ("give up", 0.50, "abandonment language"),
    ("gave up", 0.50, "abandonment language"),
    ("given up on", 0.50, "abandonment language"),
    ("dropping", 0.40, "abandonment language"),
    ("abandoning", 0.50, "abandonment language"),
    ("decided not to pursue", 0.50, "abandonment language"),
    ("no longer interested", 0.45, "abandonment language"),
    ("not worth it", 0.35, "abandonment language"),
    ("anymore", 0.20, "abandonment language"),
    ("want this goal anymore", 0.50, "abandonment language"),
]

COMPLETED_SIGNALS: List[Signal] = [
    ("it's done", 0.50, "completion language"),
    ("it is done", 0.50, "completion language"),
    ("completed the goal", 0.60, "completion language"),
    ("completed my goal", 0.60, "completion language"),
    ("achieved it", 0.50, "completion language"),
    ("achieved my goal", 0.60, "completion language"),
    ("shipped the final", 0.50, "completion language"),
    ("finally finished", 0.50, "completion language"),
    ("finished the project", 0.50, "completion language"),
    ("the project is done", 0.50, "completion language"),
    ("finished the goal", 0.55, "completion language"),
    ("goal is complete", 0.60, "completion language"),
    ("we did it", 0.45, "completion language"),
    ("all done", 0.40, "completion language"),
]

BLOCKED_SIGNALS: List[Signal] = [
    ("stuck", 0.40, "blocked language"),
    ("blocked", 0.50, "blocked language"),
    ("blocked by", 0.50, "blocked language"),
    ("waiting for", 0.40, "blocked language"),
    ("unable to", 0.40, "blocked language"),
    ("keeps failing", 0.45, "blocked language"),
    ("it's failing", 0.30, "blocked language"),
    ("isn't working", 0.35, "blocked language"),
    ("not able to", 0.35, "blocked language"),
    ("prevented", 0.40, "blocked language"),
    ("can't progress", 0.40, "blocked language"),
    ("can't move forward", 0.40, "blocked language"),
]

PROGRESS_SIGNALS: List[Signal] = [
    ("finished", 0.30, "progress language"),
    ("implemented", 0.35, "progress language"),
    ("built", 0.30, "progress language"),
    ("done", 0.25, "progress language"),
    ("shipped", 0.30, "progress language"),
    ("working on", 0.20, "active progress language"),
    ("made progress", 0.40, "progress language"),
    ("making progress", 0.40, "progress language"),
    ("fixed", 0.25, "progress language"),
    ("solved", 0.30, "progress language"),
    ("passed", 0.25, "progress language"),
    ("deployed", 0.30, "progress language"),
    ("almost done", 0.35, "progress language"),
    ("getting closer", 0.35, "progress language"),
    ("progress", 0.30, "progress language"),
]

ACTIVE_SIGNALS: List[Signal] = [
    ("still working", 0.40, "active pursuit language"),
    ("working on", 0.30, "active pursuit language"),
    ("currently working", 0.40, "active pursuit language"),
    ("i'm working", 0.30, "active pursuit language"),
    ("i am working", 0.30, "active pursuit language"),
    ("continuing", 0.30, "active pursuit language"),
    ("continuing with", 0.35, "active pursuit language"),
    ("still at it", 0.40, "active pursuit language"),
    ("back at it", 0.35, "active pursuit language"),
    ("ongoing", 0.30, "active pursuit language"),
]

# Status selection precedence: more decisive relationships win first. This keeps
# e.g. a completed whole goal from being reported as mere progress.
STATUS_PRIORITY: List[GoalStatus] = [
    GoalStatus.CHANGED,
    GoalStatus.ABANDONED,
    GoalStatus.COMPLETED,
    GoalStatus.BLOCKED,
    GoalStatus.PROGRESS,
    GoalStatus.ACTIVE,
    GoalStatus.NEW,
    GoalStatus.NONE,
]

STATUS_THRESHOLDS: Dict[GoalStatus, float] = {
    GoalStatus.CHANGED: 0.50,
    GoalStatus.ABANDONED: 0.50,
    GoalStatus.COMPLETED: 0.50,
    GoalStatus.BLOCKED: 0.35,
    GoalStatus.PROGRESS: 0.25,
    GoalStatus.ACTIVE: 0.30,
}

# ---------------------------------------------------------------------------
# Domain / topic association (deterministic, no embeddings)
# ---------------------------------------------------------------------------

# Small, controlled lexicon mapping a few common tokens to domain buckets. This
# lets the detector link a component mention ("UserStateDetector") to the
# broader project (ChronOS) and a platform word ("web") to an app goal, without
# introducing a full embedding system. Tokens absent here never associate.
TOKEN_BUCKETS: Dict[str, set] = {
    "web": {"APP"},
    "website": {"APP"},
    "mobile": {"APP"},
    "app": {"APP"},
    "dashboard": {"APP"},
    "ios": {"APP"},
    "android": {"APP"},
    "platform": {"APP"},
    "product": {"APP"},
    "saas": {"APP"},
    "chronos": {"ENGINE"},
    "opentime": {"ENGINE"},
    "engine": {"ENGINE"},
    "userstatedetector": {"ENGINE"},
    "user state detector": {"ENGINE"},
    "intentdetector": {"ENGINE"},
    "intent detector": {"ENGINE"},
    "goaldetector": {"ENGINE"},
    "goal detector": {"ENGINE"},
    "statebuilder": {"ENGINE"},
    "state builder": {"ENGINE"},
    "timelineengine": {"ENGINE"},
    "timeline engine": {"ENGINE"},
    "retrievalengine": {"ENGINE"},
    "retrieval engine": {"ENGINE"},
    "memorysystem": {"ENGINE"},
    "memory system": {"ENGINE"},
    "reflectionengine": {"ENGINE"},
    "reflection engine": {"ENGINE"},
    "patterndetector": {"ENGINE"},
    "pattern detector": {"ENGINE"},
    "identitymodel": {"ENGINE"},
    "identity profile": {"ENGINE"},
    "python": {"PROGRAMMING"},
    "rust": {"PROGRAMMING"},
    "java": {"PROGRAMMING"},
    "javascript": {"PROGRAMMING"},
    "typescript": {"PROGRAMMING"},
    "dsa": {"PROGRAMMING"},
    "algorithms": {"PROGRAMMING"},
}

STOPWORDS: set = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "at", "for",
    "with", "by", "i", "my", "me", "we", "our", "you", "your", "it", "its",
    "is", "are", "was", "were", "be", "been", "am", "than", "that", "this",
    "these", "those", "so", "as", "but", "not", "no", "do", "does", "did",
    "if", "from", "about", "into", "over", "up", "down", "all", "will",
    "would", "can", "could", "should", "have", "has", "had", "they", "them",
    "their", "he", "she", "him", "her", "just", "also", "more", "most",
    "there", "really", "very", "too",
}

_TOKENS_RE = re.compile(r"[a-z0-9]+")


class GoalDetector(BaseGoalDetector):
    """Analyzes how a user input relates to the user's goals.

    Deterministic and fully offline: new-goal detection uses weighted intention
    signals; existing-goal status uses weighted status signals; association uses
    a lightweight token/domain-bucket overlap. Identical inputs always produce
    identical results.
    """

    async def detect_goals(
        self, user_input: UserInput, existing_goals: List[str]
    ) -> GoalAnalysisResult:
        content = user_input.content or ""
        text = content.lower()

        items: List[GoalAnalysisItem] = []

        new_item = self._detect_new_goal(content, text)
        if new_item is not None:
            items.append(new_item)

        for goal in existing_goals:
            if not goal:
                continue
            matched = self._analyze_existing(text, goal)
            if matched is not None:
                items.append(matched)

        items = [it for it in items if it.status != GoalStatus.NONE]
        if not items:
            return GoalAnalysisResult(status=GoalStatus.NONE, items=[])

        items.sort(
            key=lambda it: (
                -it.confidence,
                STATUS_PRIORITY.index(it.status),
            )
        )
        primary = items[0]
        return GoalAnalysisResult(
            status=primary.status,
            goal=primary.goal or primary.matched_existing_goal,
            matched_existing_goal=primary.matched_existing_goal,
            confidence=primary.confidence,
            signals=primary.signals,
            items=items,
        )

    # ------------------------------------------------------------------
    # New-goal detection
    # ------------------------------------------------------------------

    def _detect_new_goal(
        self, content: str, text: str
    ) -> Optional[GoalAnalysisItem]:
        if not content.strip() or TRIVIAL_DESIRE.search(text):
            return None

        score = 0.0
        descriptions: List[str] = []
        for pattern, weight, desc in NEW_GOAL_SIGNALS:
            if pattern in text:
                score += weight
                if desc not in descriptions:
                    descriptions.append(desc)

        goal_phrase = self._extract_goal_phrase(content)
        first_verb = self._first_word(goal_phrase)
        verb_is_goal = first_verb in GOAL_VERBS

        if score < NEW_WITH_VERB_THRESHOLD:
            return None
        if score < NEW_STRONG_THRESHOLD and not verb_is_goal:
            return None
        if not goal_phrase:
            return None

        confidence = round(
            min(0.95, 0.30 + 0.55 * score + (0.15 if verb_is_goal else 0.0)),
            2,
        )
        return GoalAnalysisItem(
            status=GoalStatus.NEW,
            goal=goal_phrase,
            matched_existing_goal=None,
            confidence=confidence,
            signals=descriptions,
        )

    def _extract_goal_phrase(self, content: str) -> str:
        # Find the first goal-introduction phrase and take the text after it,
        # up to the end of the sentence.
        patterns = [
            re.compile(r"my goal is (?:to )?", re.IGNORECASE),
            re.compile(r"i ('m |am |'ve |have |'d |would |will |want to |plan to |need to |hope to |am working toward )", re.IGNORECASE),
            re.compile(r"working toward ", re.IGNORECASE),
            re.compile(r"i ('m |am )?going to ", re.IGNORECASE),
        ]
        best: Optional[str] = None
        best_pos = len(content) + 1
        for pat in patterns:
            m = pat.search(content)
            if m and (best is None or m.end() < best_pos):
                best_pos = m.end()
                best = content[m.end():]

        if best is None:
            return ""

        for sep in (".", "!", "?", "\n", ";"):
            idx = best.find(sep)
            if idx != -1:
                best = best[:idx]
        best = best.strip()
        if not best:
            return ""
        words = re.split(r"\s+", best)
        phrase = " ".join(words[:6]).strip()
        phrase = phrase.rstrip(".,!?:; ")
        if not phrase:
            return ""
        return phrase[0].upper() + phrase[1:]

    @staticmethod
    def _first_word(phrase: str) -> str:
        if not phrase:
            return ""
        return phrase.split()[0].lower()

    # ------------------------------------------------------------------
    # Existing-goal analysis
    # ------------------------------------------------------------------

    def _analyze_existing(self, text: str, goal: str) -> Optional[GoalAnalysisItem]:
        if not self._associated(text, goal):
            return None

        status, descriptions = self._classify_status(text, goal)

        if status == GoalStatus.NONE:
            # Associated but no explicit status language: treat as actively
            # discussed/reaffirmed pursuit, at low confidence.
            status = GoalStatus.ACTIVE
            descriptions = ["active pursuit language"]

        score = self._status_score(status, text)
        confidence = round(
            min(0.95, 0.30 + 0.60 * score + 0.03 * len(descriptions)),
            2,
        )
        return GoalAnalysisItem(
            status=status,
            goal=goal,
            matched_existing_goal=goal,
            confidence=confidence,
            signals=descriptions,
        )

    def _status_score(self, status: GoalStatus, text: str) -> float:
        table = {
            GoalStatus.CHANGED: CHANGED_SIGNALS,
            GoalStatus.ABANDONED: ABANDONED_SIGNALS,
            GoalStatus.COMPLETED: COMPLETED_SIGNALS,
            GoalStatus.BLOCKED: BLOCKED_SIGNALS,
            GoalStatus.PROGRESS: PROGRESS_SIGNALS,
            GoalStatus.ACTIVE: ACTIVE_SIGNALS,
        }[status]
        return sum(weight for pattern, weight, _ in table if pattern in text)

    def _classify_status(
        self, text: str, goal: str
    ) -> Tuple[GoalStatus, List[str]]:
        # Build score tables once.
        tables: Dict[GoalStatus, List[Signal]] = {
            GoalStatus.CHANGED: CHANGED_SIGNALS,
            GoalStatus.ABANDONED: ABANDONED_SIGNALS,
            GoalStatus.COMPLETED: COMPLETED_SIGNALS,
            GoalStatus.BLOCKED: BLOCKED_SIGNALS,
            GoalStatus.PROGRESS: PROGRESS_SIGNALS,
            GoalStatus.ACTIVE: ACTIVE_SIGNALS,
        }
        scores: Dict[GoalStatus, float] = {}
        descriptions: Dict[GoalStatus, List[str]] = {}
        for status, signals in tables.items():
            s = 0.0
            descs: List[str] = []
            for pattern, weight, desc in signals:
                if pattern in text:
                    s += weight
                    if desc not in descs:
                        descs.append(desc)
            scores[status] = s
            descriptions[status] = descs

        # Completion must reference the whole goal, not a single finished piece.
        if scores[GoalStatus.COMPLETED] >= STATUS_THRESHOLDS[GoalStatus.COMPLETED]:
            if not self._whole_goal_completed(text, goal):
                scores[GoalStatus.COMPLETED] = 0.0

        for status in STATUS_PRIORITY:
            if status not in scores:
                continue
            if scores[status] >= STATUS_THRESHOLDS.get(status, 0.0):
                return status, descriptions[status]
        return GoalStatus.NONE, []

    def _whole_goal_completed(self, text: str, goal: str) -> bool:
        """True only when completion is about the goal as a whole."""
        generic_endings = [
            "the project", "the whole thing", "everything", "the goal",
            "it", "this", "my goal",
        ]
        goal_words = set(_TOKENS_RE.findall(goal.lower()))
        goal_words.discard("build")
        goal_words.discard("learn")
        goal_words.discard("deploy")
        goal_words.discard("make")
        goal_words.discard("create")
        # If the finished object words are present in the text, the whole goal
        # has been completed ("finished my portfolio website").
        matched = goal_words & set(_TOKENS_RE.findall(text))
        has_generic = any(g in text for g in generic_endings)
        return bool(matched) or has_generic

    # ------------------------------------------------------------------
    # Association
    # ------------------------------------------------------------------

    def _associated(self, text: str, goal: str) -> bool:
        input_words = set(self._meaningful(self._tokens(text)))
        goal_words = self._meaningful(self._tokens(goal))

        if not goal_words:
            return False

        literal_overlap = set(goal_words) & input_words
        goal_buckets: set = set()
        input_buckets: set = set()
        for w in goal_words:
            goal_buckets |= TOKEN_BUCKETS.get(w, set())
        for w in self._tokens(text):
            input_buckets |= TOKEN_BUCKETS.get(w, set())

        return bool(literal_overlap) or bool(goal_buckets & input_buckets)

    @staticmethod
    def _tokens(s: str) -> List[str]:
        return _TOKENS_RE.findall(s.lower())

    @staticmethod
    def _meaningful(words: List[str]) -> List[str]:
        return [w for w in words if w not in STOPWORDS]
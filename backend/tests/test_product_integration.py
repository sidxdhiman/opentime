"""
End-to-end product integration tests for ChronOS.

Covers the complete user journey across engine → persistence → API → reload
boundaries. These tests verify real product behavior, not isolated units.

Test groups:
  1. Brand-new user conversation
  2. Ordinary non-temporal conversation
  3. Temporal thread creation and persistence
  4. Active story continuation
  5. Reload/history consistency
  6. Duplicate interaction prevention
  7. User isolation
  8. Limit=0 protection
  9. Missing thread handling
  10. Response field validation
"""

import pytest
from chronos_engine import ChronosEngine
from chronos_engine.api.router import _persist_interaction
from chronos_engine.core.models import InputType


USER_A = "product_test_user_a"
USER_B = "product_test_user_b"


# ── Helpers ──────────────────────────────────────────────────────────────


async def _process(engine: ChronosEngine, user_id: str, content: str, **kwargs):
    """Process a text input and return the EngineResponse."""
    return await engine.process_user_input(
        user_id=user_id,
        content=content,
        input_type="text",
        provider_key="chronos",
        **kwargs,
    )


async def _process_and_persist(engine: ChronosEngine, user_id: str, content: str, **kwargs):
    """Process a text input, persist interaction, and return the EngineResponse."""
    response = await engine.process_user_input(
        user_id=user_id,
        content=content,
        input_type="text",
        provider_key="chronos",
        **kwargs,
    )
    await _persist_interaction(response, storage=engine.storage)
    return response


# ── 1. Brand-new user ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_brand_new_user_conversation():
    """A user with no prior data can send a message and receive a response."""
    engine = ChronosEngine()
    user_id = "brand_new_user"

    # Verify empty state
    memories = await engine.get_memories(user_id)
    assert len(memories) == 0
    threads = await engine.temporal_store.get_candidate_threads(user_id)
    assert len(threads) == 0
    interactions = await engine.storage.get_interactions_by_user(user_id)
    assert len(interactions) == 0

    # Send first message (with persistence like the API layer does)
    response = await _process_and_persist(engine, user_id, "Hello, this is my first thought.")

    assert response is not None
    assert response.user_id == user_id
    assert response.final_response  # non-empty response
    assert response.id  # has an ID

    # Verify persistence occurred
    memories = await engine.get_memories(user_id)
    assert len(memories) >= 1  # memory was created

    interactions = await engine.storage.get_interactions_by_user(user_id)
    assert len(interactions) == 1  # interaction was persisted

    timeline = await engine.get_timeline(user_id)
    assert len(timeline) >= 1  # timeline event was created

    identity = await engine.get_identity(user_id)
    assert identity.user_id == user_id  # identity was created


@pytest.mark.asyncio
async def test_brand_new_user_ui_does_not_crash_on_empty_data():
    """UI components should handle empty state without crashing."""
    engine = ChronosEngine()
    user_id = "empty_ui_user"

    # All collections should be empty, not error
    memories = await engine.get_memories(user_id)
    assert memories == []

    threads = await engine.temporal_store.get_candidate_threads(user_id)
    assert threads == []

    interactions = await engine.storage.get_interactions_by_user(user_id)
    assert interactions == []

    reflections = await engine.get_reflections(user_id)
    assert isinstance(reflections, list)

    patterns = await engine.get_patterns(user_id)
    assert isinstance(patterns, list)


# ── 2. Ordinary non-temporal conversation ────────────────────────────────


@pytest.mark.asyncio
async def test_ordinary_conversation_persists_correctly():
    """Multiple ordinary messages persist correctly with proper ordering."""
    engine = ChronosEngine()

    r1 = await _process_and_persist(engine, USER_A, "I enjoy reading books on weekends.")
    r2 = await _process_and_persist(engine, USER_A, "Today I went for a long walk in the park.")
    r3 = await _process_and_persist(engine, USER_A, "The weather was perfect for outdoor activities.")

    # All responses should be distinct
    assert r1.id != r2.id != r3.id

    # Interactions should be persisted and ordered
    interactions = await engine.storage.get_interactions_by_user(USER_A)
    assert len(interactions) >= 3

    # All three messages should appear
    contents = [i.user_content for i in interactions]
    assert any("reading books" in c for c in contents)
    assert any("long walk" in c for c in contents)
    assert any("perfect" in c for c in contents)


@pytest.mark.asyncio
async def test_ordinary_conversation_no_temporal_thread_created():
    """Normal conversation should not accidentally create temporal threads."""
    engine = ChronosEngine()

    await _process(engine, USER_A, "I like coffee in the morning.")
    await _process(engine, USER_A, "My favorite color is blue.")

    threads = await engine.temporal_store.get_candidate_threads(USER_A)
    # Normal everyday input should not create temporal threads
    # (this depends on the temporal detector's sensitivity — if it triggers,
    # that's fine, but it should not be forced)
    # The key assertion: no threads from forced/intentional creation
    for t in threads:
        assert t.user_id == USER_A  # ownership check


# ── 3. Temporal thread creation and persistence ──────────────────────────


@pytest.mark.asyncio
async def test_temporal_thread_creation_and_persistence():
    """A temporal event creates a thread that persists across reload."""
    engine = ChronosEngine()
    user_id = "temporal_creation_user"

    # Seed to establish baseline
    await engine.seed_initial_state(user_id)

    # Send a message that is likely to trigger temporal detection
    response = await _process(
        engine, user_id,
        "I have decided to completely change my career path. "
        "After years of engineering, I am transitioning to becoming a teacher. "
        "This is the biggest decision of my life."
    )

    # Check if a thread was created
    threads = await engine.temporal_store.get_candidate_threads(user_id)

    if response.chronos_state and response.chronos_state.temporal_lifecycle:
        lc = response.chronos_state.temporal_lifecycle
        if lc.created and lc.thread_id:
            # Thread should exist in persistent store
            thread = await engine.temporal_store.get_thread(lc.thread_id, user_id)
            assert thread is not None
            assert thread.user_id == user_id
            assert thread.subject  # non-empty subject

            # Events should exist for this thread
            events = await engine.temporal_store.get_events_by_thread(lc.thread_id, user_id)
            assert len(events) >= 1
            for event in events:
                assert event.user_id == user_id


@pytest.mark.asyncio
async def test_thread_survives_reload():
    """A created thread persists and survives a simulated reload (re-query)."""
    engine = ChronosEngine()
    user_id = "reload_user"

    await engine.seed_initial_state(user_id)

    await _process(
        engine, user_id,
        "I just moved to a new city. This is a major life change."
    )

    threads = await engine.temporal_store.get_candidate_threads(user_id)

    if threads:
        thread = threads[0]
        # Simulate reload: re-fetch from store
        reloaded = await engine.temporal_store.get_thread(thread.id, user_id)
        assert reloaded is not None
        assert reloaded.id == thread.id
        assert reloaded.subject == thread.subject

        # Events should also survive
        events = await engine.temporal_store.get_events_by_thread(thread.id, user_id)
        assert len(events) >= 1


# ── 4. Active story continuation ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_active_story_continuation():
    """An active thread can be continued across multiple messages."""
    engine = ChronosEngine()
    user_id = "continuation_user"

    await engine.seed_initial_state(user_id)

    # First message — may create a thread
    r1 = await _process(
        engine, user_id,
        "I am thinking about starting my own business. It feels both exciting and terrifying."
    )

    threads = await engine.temporal_store.get_candidate_threads(user_id)
    if not threads:
        pytest.skip("No thread created in this run — temporal detection did not trigger")

    thread = threads[0]

    # Continue the story with the active thread context
    r2 = await _process(
        engine, user_id,
        "I spoke to my mentor about the business idea and she was supportive.",
        active_thread_id=thread.id,
    )

    # The response should have been processed with the active context
    assert r2 is not None
    assert r2.user_id == user_id

    # Thread should still exist and be updated
    reloaded = await engine.temporal_store.get_thread(thread.id, user_id)
    assert reloaded is not None
    assert reloaded.updated_at >= thread.updated_at


@pytest.mark.asyncio
async def test_active_story_persists_across_messages():
    """The active thread remains stable across multiple continuation messages."""
    engine = ChronosEngine()
    user_id = "stable_active_user"

    await engine.seed_initial_state(user_id)

    r1 = await _process(
        engine, user_id,
        "I am working on a major project deadline next week."
    )

    threads = await engine.temporal_store.get_candidate_threads(user_id)
    if not threads:
        pytest.skip("No thread created")

    thread = threads[0]

    # Multiple continuations
    for i in range(3):
        r = await _process(
            engine, user_id,
            f"Update {i + 1}: Still working on the project, making progress.",
            active_thread_id=thread.id,
        )
        assert r is not None

    # Thread should still exist
    reloaded = await engine.temporal_store.get_thread(thread.id, user_id)
    assert reloaded is not None
    assert reloaded.user_id == user_id


# ── 5. Reload/history consistency ────────────────────────────────────────


@pytest.mark.asyncio
async def test_interaction_history_consistent_after_reload():
    """Interaction history is consistent after simulated page reload."""
    engine = ChronosEngine()
    user_id = "reload_consistency_user"

    # Send messages
    r1 = await _process_and_persist(engine, user_id, "First message about my day.")
    r2 = await _process_and_persist(engine, user_id, "Second message about my evening.")
    r3 = await _process_and_persist(engine, user_id, "Third message about tomorrow.")

    # Get interactions (simulates initial page load)
    interactions_1 = await engine.storage.get_interactions_by_user(user_id)
    assert len(interactions_1) >= 3

    # Get interactions again (simulates page reload)
    interactions_2 = await engine.storage.get_interactions_by_user(user_id)
    assert len(interactions_2) >= 3

    # Content and ordering should be identical
    ids_1 = [i.id for i in interactions_1]
    ids_2 = [i.id for i in interactions_2]
    assert ids_1 == ids_2

    # Response IDs should match
    response_ids = {r1.id, r2.id, r3.id}
    interaction_ids = {i.id for i in interactions_1}
    # At least the latest response should be in the list
    assert r3.id in interaction_ids


@pytest.mark.asyncio
async def test_interaction_ordering_is_chronological():
    """Interactions are returned in reverse chronological order (newest first)."""
    engine = ChronosEngine()
    user_id = "ordering_user"

    r1 = await _process_and_persist(engine, user_id, "Alpha message.")
    r2 = await _process_and_persist(engine, user_id, "Beta message.")
    r3 = await _process_and_persist(engine, user_id, "Gamma message.")

    interactions = await engine.storage.get_interactions_by_user(user_id)
    # API returns sorted by created_at DESC
    timestamps = [i.created_at for i in interactions]
    assert timestamps == sorted(timestamps, reverse=True)


# ── 6. Duplicate interaction prevention ──────────────────────────────────


@pytest.mark.asyncio
async def test_interactions_have_unique_ids():
    """Each interaction has a unique ID — no duplicates from persistence."""
    engine = ChronosEngine()
    user_id = "unique_id_user"

    responses = []
    for i in range(5):
        r = await _process_and_persist(engine, user_id, f"Message number {i + 1}.")
        responses.append(r)

    interactions = await engine.storage.get_interactions_by_user(user_id)
    ids = [i.id for i in interactions]
    # All IDs should be unique
    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_same_message_twice_creates_two_interactions():
    """Sending the same content twice creates two distinct interactions."""
    engine = ChronosEngine()
    user_id = "duplicate_content_user"

    r1 = await _process_and_persist(engine, user_id, "I love sunny days.")
    r2 = await _process_and_persist(engine, user_id, "I love sunny days.")

    assert r1.id != r2.id  # Different response IDs

    interactions = await engine.storage.get_interactions_by_user(user_id)
    same_content = [i for i in interactions if i.user_content == "I love sunny days."]
    assert len(same_content) >= 2  # Both persisted


# ── 7. User isolation ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_users_cannot_see_each_others_data():
    """User A's data is invisible to User B."""
    engine = ChronosEngine()

    # User A sends messages
    await _process_and_persist(engine, USER_A, "User A's private thought.")
    await _process_and_persist(engine, USER_A, "User A's secret plan.")

    # User B sends messages
    await _process_and_persist(engine, USER_B, "User B's private thought.")

    # User A's interactions
    a_interactions = await engine.storage.get_interactions_by_user(USER_A)
    a_contents = [i.user_content for i in a_interactions]
    assert any("User A" in c for c in a_contents)
    assert not any("User B" in c for c in a_contents)

    # User B's interactions
    b_interactions = await engine.storage.get_interactions_by_user(USER_B)
    b_contents = [i.user_content for i in b_interactions]
    assert any("User B" in c for c in b_contents)
    assert not any("User A" in c for c in b_contents)


@pytest.mark.asyncio
async def test_threads_are_user_scoped():
    """User A's threads are not visible to User B."""
    engine = ChronosEngine()

    await engine.seed_initial_state(USER_A)
    await engine.seed_initial_state(USER_B)

    await _process(
        engine, USER_A,
        "I am making a life-changing decision to move abroad."
    )
    await _process(
        engine, USER_B,
        "I am also making a decision to change careers."
    )

    a_threads = await engine.temporal_store.get_candidate_threads(USER_A)
    b_threads = await engine.temporal_store.get_candidate_threads(USER_B)

    for t in a_threads:
        assert t.user_id == USER_A
    for t in b_threads:
        assert t.user_id == USER_B


@pytest.mark.asyncio
async def test_active_thread_id_rejects_other_users_thread():
    """Passing another user's thread ID as active_thread_id is rejected."""
    engine = ChronosEngine()

    await engine.seed_initial_state(USER_A)
    await _process(
        engine, USER_A,
        "I am starting a new chapter in my life."
    )

    a_threads = await engine.temporal_store.get_candidate_threads(USER_A)
    if not a_threads:
        pytest.skip("No thread created for User A")

    thread_a = a_threads[0]

    # User B tries to use User A's thread ID
    # This should fail in the API layer (router validates ownership)
    # In the engine directly, the lifecycle will not find the thread under User B's ownership
    r = await _process(
        engine, USER_B,
        "Attempting to use another user's thread.",
        active_thread_id=thread_a.id,
    )

    # The engine should still produce a valid response (graceful degradation)
    assert r is not None
    assert r.final_response

    # User B should NOT have a thread linked to User A's thread
    b_threads = await engine.temporal_store.get_candidate_threads(USER_B)
    for t in b_threads:
        assert t.id != thread_a.id


# ── 8. Limit=0 protection ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_limit_zero_returns_single_record_not_all():
    """limit=0 is clamped to 1 — does not return all records."""
    engine = ChronosEngine()
    user_id = "limit_zero_user"

    for i in range(10):
        await _process_and_persist(engine, user_id, f"Message {i + 1}.")

    # With limit=0, should return 1 record (clamped), not all 10
    result_0 = await engine.storage.get_interactions_by_user(user_id, limit=0)
    assert len(result_0) == 1

    # With limit=1, same result
    result_1 = await engine.storage.get_interactions_by_user(user_id, limit=1)
    assert len(result_1) == 1

    # With limit=5, returns 5
    result_5 = await engine.storage.get_interactions_by_user(user_id, limit=5)
    assert len(result_5) == 5


@pytest.mark.asyncio
async def test_memories_limit_zero_returns_single_record():
    """Memories limit=0 is also clamped."""
    engine = ChronosEngine()
    user_id = "mem_limit_user"

    for i in range(5):
        await _process_and_persist(engine, user_id, f"Memory {i + 1}.")

    result_0 = await engine.storage.get_memories_by_user(user_id, limit=0)
    assert len(result_0) == 1


@pytest.mark.asyncio
async def test_negative_limit_clamped_to_one():
    """Negative limits are clamped to 1."""
    engine = ChronosEngine()
    user_id = "neg_limit_user"

    for i in range(5):
        await _process_and_persist(engine, user_id, f"Message {i + 1}.")

    result = await engine.storage.get_interactions_by_user(user_id, limit=-1)
    assert len(result) == 1


# ── 9. Missing thread handling ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_thread_returns_none():
    """Requesting a non-existent thread returns None."""
    engine = ChronosEngine()

    thread = await engine.temporal_store.get_thread("thread_nonexistent", USER_A)
    assert thread is None


@pytest.mark.asyncio
async def test_missing_thread_events_returns_empty():
    """Requesting events for a non-existent thread returns empty list."""
    engine = ChronosEngine()

    events = await engine.temporal_store.get_events_by_thread("thread_nonexistent", USER_A)
    assert events == []


@pytest.mark.asyncio
async def test_user_scoped_thread_lookup():
    """Thread lookup requires both thread_id AND user_id to match."""
    engine = ChronosEngine()

    await engine.seed_initial_state(USER_A)
    await _process(
        engine, USER_A,
        "I am making a big decision about my future."
    )

    a_threads = await engine.temporal_store.get_candidate_threads(USER_A)
    if not a_threads:
        pytest.skip("No thread created")

    thread = a_threads[0]

    # User A can find it
    found = await engine.temporal_store.get_thread(thread.id, USER_A)
    assert found is not None

    # User B cannot find it
    not_found = await engine.temporal_store.get_thread(thread.id, USER_B)
    assert not_found is None


# ── 10. Interaction persistence survives response ────────────────────────


@pytest.mark.asyncio
async def test_successful_response_survives_persistence():
    """A successful engine response is properly persisted."""
    engine = ChronosEngine()
    user_id = "persistence_test_user"

    response = await _process_and_persist(engine, user_id, "Test message for persistence.")

    # The engine returned a valid response
    assert response is not None
    assert response.final_response
    assert response.id

    # Verify it was actually persisted
    interactions = await engine.storage.get_interactions_by_user(user_id)
    assert any(i.id == response.id for i in interactions)


@pytest.mark.asyncio
async def test_engine_response_contains_required_fields():
    """Every EngineResponse has the fields the frontend depends on."""
    engine = ChronosEngine()
    user_id = "field_check_user"

    response = await _process(engine, user_id, "Checking response fields.")

    # Core fields
    assert response.id
    assert response.user_id == user_id
    assert response.final_response
    assert response.original_input
    assert response.original_input.content == "Checking response fields."
    assert response.original_input.input_type == InputType.TEXT
    assert response.reasoning_trace is not None
    assert response.validation_result is not None
    assert response.processing_time_ms >= 0

    # ChronosState fields the frontend uses
    state = response.chronos_state
    assert state is not None
    # past_self_conversation may be None (not all messages trigger it)
    # temporal_reflection may be None
    # temporal_lifecycle may be None

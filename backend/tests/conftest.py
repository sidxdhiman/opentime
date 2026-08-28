"""
pytest fixtures for onboarding and Chronos tests.

Uses mongomock-motor to provide an in-memory MongoDB that works with
the Motor async driver — no real MongoDB required.
"""
from datetime import datetime, timezone
from uuid import UUID

import pytest
from mongomock_motor import AsyncMongoMockClient

from opentime.api.dependencies import get_current_user
from opentime.main import app as opentime_app
from opentime.application.auth.dto import UserResponse

from opentime.infrastructure.mongodb.chronos_repos import (
    MongoAnalysisPreferenceRepository,
    MongoChronosStateRepository,
    MongoGoalRepository,
    MongoIdentityStateRepository,
    MongoMemoryRepository,
    MongoPatternRepository,
    MongoTimelineRepository,
)
from opentime.infrastructure.mongodb.onboarding_repos import (
    MongoOnboardingResponseRepository,
    MongoOnboardingSessionRepository,
)
from opentime.infrastructure.services.embedding_service import MockEmbeddingService
from opentime.infrastructure.services.llm_service import MockLLMService
from opentime.application.onboarding.service import OnboardingService
from opentime.application.onboarding.init_service import ChronosInitializationService

# Deterministic user IDs used to authenticate ChronOS engine API tests
# without a live Postgres/MySQL user store.  `get_current_user` is overridden
# to return a UserResponse whose id stringifies to one of these.
AUTH_USER_ID = "11111111-1111-4111-8111-111111111111"
OTHER_AUTH_USER_ID = "22222222-2222-4222-8222-222222222222"


def make_user_response(user_id: str) -> UserResponse:
    now = datetime.now(timezone.utc)
    return UserResponse(
        id=UUID(user_id),
        email="test@opentime.ai",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def auth_user_id() -> str:
    return AUTH_USER_ID


@pytest.fixture
def override_auth(auth_user_id: str) -> str:
    """Override the app's get_current_user dependency with a fake user.

    The authenticated user's id string equals ``auth_user_id`` so that data
    stored under that key is visible to the request.  The override is removed
    after the test to avoid leaking into other tests.
    """

    async def _dep() -> UserResponse:
        return make_user_response(auth_user_id)

    opentime_app.dependency_overrides[get_current_user] = _dep
    yield auth_user_id
    opentime_app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_db():
    """In-memory Motor-compatible MongoDB database."""
    client = AsyncMongoMockClient()
    return client["opentime_test"]


@pytest.fixture
def session_repo(mock_db):
    return MongoOnboardingSessionRepository(mock_db)


@pytest.fixture
def response_repo(mock_db):
    return MongoOnboardingResponseRepository(mock_db)


@pytest.fixture
def memory_repo(mock_db):
    return MongoMemoryRepository(mock_db)


@pytest.fixture
def identity_repo(mock_db):
    return MongoIdentityStateRepository(mock_db)


@pytest.fixture
def goal_repo(mock_db):
    return MongoGoalRepository(mock_db)


@pytest.fixture
def timeline_repo(mock_db):
    return MongoTimelineRepository(mock_db)


@pytest.fixture
def pattern_repo(mock_db):
    return MongoPatternRepository(mock_db)


@pytest.fixture
def pref_repo(mock_db):
    return MongoAnalysisPreferenceRepository(mock_db)


@pytest.fixture
def chronos_repo(mock_db):
    return MongoChronosStateRepository(mock_db)


@pytest.fixture
def onboarding_service(session_repo, response_repo):
    return OnboardingService(session_repo=session_repo, response_repo=response_repo)


@pytest.fixture
def chronos_init_service(
    memory_repo, identity_repo, goal_repo, timeline_repo,
    pattern_repo, pref_repo, chronos_repo,
):
    return ChronosInitializationService(
        memory_repo=memory_repo,
        identity_repo=identity_repo,
        goal_repo=goal_repo,
        timeline_repo=timeline_repo,
        pattern_repo=pattern_repo,
        pref_repo=pref_repo,
        chronos_repo=chronos_repo,
        llm=MockLLMService(),
        embedding=MockEmbeddingService(),
    )

"""
pytest fixtures for onboarding and Chronos tests.

Uses mongomock-motor to provide an in-memory MongoDB that works with
the Motor async driver — no real MongoDB required.
"""
import pytest
from mongomock_motor import AsyncMongoMockClient

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

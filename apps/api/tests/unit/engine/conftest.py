"""Fixtures for the engine tests."""

from collections.abc import Callable

import pytest

from app.content.loader import LoadedCase, load_case
from app.domain.case import VariantId
from tests.unit.engine.play import DEV_001, Play


@pytest.fixture(scope="session")
def dev001() -> LoadedCase:
    return load_case(DEV_001)


@pytest.fixture
def play(dev001: LoadedCase) -> Callable[[VariantId], Play]:
    return lambda variant="A": Play(dev001, variant)

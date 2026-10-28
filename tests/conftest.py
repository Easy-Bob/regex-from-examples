import pytest

from contract import Format, FormatInput
from plugin import pin_target


@pytest.fixture(scope="session")
def pinned(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """Each format's answer key, as NanoAgent pins it before the agent starts."""
    return {fmt: pin_target(FormatInput(format=fmt), tmp_path_factory.mktemp(fmt.value)) for fmt in Format}

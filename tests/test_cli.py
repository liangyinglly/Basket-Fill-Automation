import pytest

from app.cli import main


def test_search_command_is_not_implemented():
    with pytest.raises(NotImplementedError):
        main(["search", "--basket-path", "sample-basket.json"])


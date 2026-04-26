from app.cli import main


def test_search_command_runs_without_crashing():
    assert main(["search", "--basket-path", "sample-basket.json"]) == 0

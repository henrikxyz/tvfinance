from tvfinance.providers import CAPABILITIES, capabilities


def test_capability_inventory_is_complete_and_immutable() -> None:
    inventory = capabilities()
    assert inventory is CAPABILITIES
    assert {item.name for item in inventory} == {
        "search",
        "quotes",
        "quote_stream",
        "history",
        "screener",
        "options",
        "news",
        "calendars",
        "research",
    }
    assert all(item.contract_fixture for item in inventory)
    assert {item.name for item in inventory if item.live_check} == {
        "search",
        "quotes",
    }

"""Keep existing entries and user settings when migrating."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ortsnetz_auslastung import async_migrate_entry
from custom_components.ortsnetz_auslastung.const import DOMAIN


@pytest.mark.parametrize("version", [1, 2])
async def test_legacy_entry_loses_token_without_losing_settings(hass, version):
    data = {"api_url": "https://example.test", "latitude": 52.5,
            "longitude": 13.4, "l1_entity": "sensor.l1", "token": "old-secret"}
    options = {"smartmeter_model": "My meter"}
    entry = MockConfigEntry(domain=DOMAIN, version=version, title="Old title",
                            data=data, options=options, unique_id="existing-location")
    entry.add_to_hass(hass)
    original_id = entry.entry_id

    assert await async_migrate_entry(hass, entry)

    assert entry.version == 3
    assert entry.title == "Ortsnetz-Auslastung"
    assert dict(entry.data) == {key: value for key, value in data.items() if key != "token"}
    assert dict(entry.options) == options
    assert entry.entry_id == original_id
    assert entry.unique_id == "existing-location"


async def test_current_entry_is_unchanged(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=3, title="My custom name",
                            data={"latitude": 52.5})
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    assert entry.title == "My custom name"
    assert dict(entry.data) == {"latitude": 52.5}

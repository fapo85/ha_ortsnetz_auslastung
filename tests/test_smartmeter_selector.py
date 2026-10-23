"""Smart meter suggestions must preserve optional free-text configuration."""

from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import selector
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ortsnetz_auslastung import _send
from custom_components.ortsnetz_auslastung.config_flow import _settings_schema
from custom_components.ortsnetz_auslastung.const import DOMAIN
from custom_components.ortsnetz_auslastung.smartmeters import SMARTMETER_MODELS

URL = "https://example.test/v1/measurements"
PHASES = {"l1_entity": "sensor.l1", "l2_entity": "sensor.l2", "l3_entity": "sensor.l3"}


def _form(**optional):
    return {"api_url": URL, "phase_voltages": PHASES, **optional}


def test_suggestions_are_unique_sorted_and_bounded():
    assert list(SMARTMETER_MODELS) == sorted(set(SMARTMETER_MODELS), key=str.casefold)
    assert all(0 < len(model) <= 120 for model in SMARTMETER_MODELS)
    assert {"Shelly Pro 3EM", "Apator APOX+", "SMA Sunny Home Manager 2.0"} <= set(SMARTMETER_MODELS)
    assert not any("Heater" in model or "Multical" in model or "SUN2000" in model for model in SMARTMETER_MODELS)


def test_schema_exposes_optional_dropdown_with_custom_values(hass):
    schema = _settings_schema(hass, {})
    key = next(key for key in schema.schema if key == "smartmeter_model")
    assert isinstance(key, vol.Optional)
    assert key.default is vol.UNDEFINED
    field = schema.schema[key]
    assert isinstance(field, selector.SelectSelector)
    assert field.config["mode"] == "dropdown"
    assert field.config["custom_value"] is True
    assert field.config["sort"] is True
    assert field.config["options"] == list(SMARTMETER_MODELS)
    assert field("My custom meter") == "My custom meter"
    assert field("Shelly Pro 3EM") == "Shelly Pro 3EM"


@pytest.mark.parametrize("model", [None, "", "Shelly Pro 3EM", "Eigener Zähler ä/Ö", "x" * 120])
async def test_setup_accepts_optional_known_and_custom_models(hass, model):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    optional = {} if model is None else {"smartmeter_model": model}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], _form(**optional))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["smartmeter_model"] == model


@pytest.mark.parametrize("options", [False, True])
async def test_overlong_model_reports_field_error(hass, options):
    if options:
        entry = MockConfigEntry(domain=DOMAIN, version=3, data={"api_url": URL, **PHASES})
        entry.add_to_hass(hass)
        result = await hass.config_entries.options.async_init(entry.entry_id)
        configure = hass.config_entries.options.async_configure
    else:
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        configure = hass.config_entries.flow.async_configure
    result = await configure(result["flow_id"], _form(smartmeter_model="x" * 121))
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"smartmeter_model": "invalid_smartmeter_model"}


@pytest.mark.parametrize("model", ["Shelly Pro 3EM", "Mein alter Zähler"])
async def test_options_preserve_model_and_send_same_string(hass, aioclient_mock, model):
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={
        "api_url": URL, **PHASES, "latitude": 52.5, "longitude": 13.4,
        "smartmeter_model": model,
    })
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    key = next(key for key in result["data_schema"].schema if key == "smartmeter_model")
    assert key.description == {"suggested_value": model}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _form(smartmeter_model=model)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["smartmeter_model"] == model
    for entity_id in PHASES.values():
        hass.states.async_set(entity_id, "230")
    aioclient_mock.post(URL, json={})
    with patch("custom_components.ortsnetz_auslastung.asyncio.sleep"):
        await _send(hass, entry)
    assert aioclient_mock.mock_calls[0][2]["smartmeter_model"] == model

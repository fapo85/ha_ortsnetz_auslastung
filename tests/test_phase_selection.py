"""Phase selection supports sensors, explicit -1 and clearing existing choices."""

import json
from pathlib import Path
import re
from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.data_entry_flow import FlowManagerIndexView
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ortsnetz_auslastung import _send
from custom_components.ortsnetz_auslastung.const import DOMAIN

URL = "https://example.test/v1/measurements"
PHASES = {f"l{phase}_entity": f"sensor.l{phase}" for phase in (1, 2, 3)}


def _entry(hass):
    for phase in (1, 2, 3):
        hass.states.async_set(f"sensor.l{phase}", "230", {"unit_of_measurement": "V"})
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={
        "api_url": URL, **PHASES, "latitude": 52.5, "longitude": 13.4,
    })
    entry.add_to_hass(hass)
    return entry


async def test_phase_dropdown_accepts_custom_values_and_preserves_saved_sensors(hass):
    entry = _entry(hass)
    hass.states.async_set("sensor.l1", "230", {"friendly_name": "Smartmeter Spannung L1", "unit_of_measurement": "V"})
    hass.states.async_remove("sensor.l3")
    hass.states.async_set("light.test", "on")
    result = await hass.config_entries.options.async_init(entry.entry_id)
    fields = result["data_schema"].schema["phase_voltages"].schema.schema
    for name, entity in PHASES.items():
        key = next(key for key in fields if key == name)
        assert isinstance(key, vol.Optional)
        assert key.default is vol.UNDEFINED
        assert key.description == {"suggested_value": entity}
    rendered = FlowManagerIndexView(hass.config_entries.options)._prepare_result_json(result)
    json.dumps(rendered)
    section = next(item for item in rendered["data_schema"] if item["name"] == "phase_voltages")
    for field in section["schema"]:
        config = field["selector"]["select"]
        assert config["custom_value"] is True
        assert config["translation_key"] == "phase_sensor"
        options = {option["value"]: option["label"] for option in config["options"]}
        assert options["not_measured"] == "Phase not measured (-1)"
        assert "-1" not in options
        assert options["sensor.l1"] == "Smartmeter Spannung L1 (sensor.l1)"
        assert options["sensor.l3"] == "sensor.l3"
        assert "light.test" not in options
        assert config["options"][0]["value"] == "not_measured"
        labels = [option["label"] for option in config["options"][1:]]
        assert labels == sorted(labels, key=str.casefold)


@pytest.mark.parametrize("language,label", [("de", "Phase nicht gemessen (-1)"), ("en", "Phase not measured (-1)")])
async def test_excluded_phase_option_is_translated(hass, language, label):
    translations = await async_get_translations(hass, language, "selector", {DOMAIN})
    assert translations[f"component.{DOMAIN}.selector.phase_sensor.options.not_measured"] == label


@pytest.mark.parametrize("language", ["de", "en"])
def test_selector_translation_option_keys_follow_hassfest_rules(language):
    path = Path(__file__).parents[1] / "custom_components" / DOMAIN / "translations" / f"{language}.json"
    translations = json.loads(path.read_text())
    for selector in translations["selector"].values():
        for option in selector["options"]:
            assert re.fullmatch(r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?", option)


@pytest.mark.parametrize("phase", (1, 2, 3))
@pytest.mark.parametrize("excluded", ("not_measured", "-1", "", None))
async def test_setup_supports_any_single_phase(hass, phase, excluded):
    selection = {f"l{phase}_entity": f"sensor.l{phase}"}
    if excluded is not None:
        selection.update({key: excluded for key in PHASES if key not in selection})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    with patch("custom_components.ortsnetz_auslastung.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {
            "api_url": URL, "phase_voltages": selection,
        })
    assert result["type"] is FlowResultType.CREATE_ENTRY
    for key, entity in PHASES.items():
        assert result["data"][key] == (entity if key == f"l{phase}_entity" else "-1")


@pytest.mark.parametrize("phase", (1, 2, 3))
@pytest.mark.parametrize("excluded", ("not_measured", "-1", "", None))
async def test_existing_phases_can_be_cleared_or_set_to_minus_one(hass, aioclient_mock, phase, excluded):
    entry = _entry(hass)
    selection = {f"l{phase}_entity": f"sensor.l{phase}"}
    if excluded is not None:
        selection.update({key: excluded for key in PHASES if key not in selection})
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "api_url": URL, "phase_voltages": selection,
    })
    assert result["type"] is FlowResultType.CREATE_ENTRY
    aioclient_mock.post(URL, json={})
    await _send(hass, entry)
    assert aioclient_mock.call_count == 1
    payload = aioclient_mock.mock_calls[0][2]
    for p in (1, 2, 3):
        assert payload[f"l{p}_v"] == (230 if p == phase else -1)
    reopened = await hass.config_entries.options.async_init(entry.entry_id)
    fields = reopened["data_schema"].schema["phase_voltages"].schema.schema
    for name in PHASES:
        key = next(key for key in fields if key == name)
        expected = "not_measured" if entry.options[name] == "-1" else entry.options[name]
        assert key.description["suggested_value"] == expected


@pytest.mark.parametrize("selection", [{}, dict.fromkeys(PHASES, "not_measured"), dict.fromkeys(PHASES, "-1"), dict.fromkeys(PHASES, " ")])
async def test_setup_and_options_reject_all_excluded_phases(hass, selection):
    form = {"api_url": URL, "phase_voltages": selection}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], form)
    assert result["errors"] == {"base": "no_measured_phase"}
    entry = _entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], form)
    assert result["errors"] == {"base": "no_measured_phase"}
    assert entry.options == {}


@pytest.mark.parametrize("selection", ["-2", "0", "230", "light.test", "sensor.", "invalid"])
async def test_only_sensor_entities_or_minus_one_are_accepted(hass, selection):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {
        "api_url": URL, "phase_voltages": {**PHASES, "l2_entity": selection},
    })
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_phase_selection"}


@pytest.mark.parametrize("state", [None, "unavailable", "unknown", "nan", "0", "149"])
async def test_selected_sensor_failure_blocks_transmission(hass, aioclient_mock, caplog, state):
    entry = _entry(hass)
    hass.config_entries.async_update_entry(entry, options={"l2_entity": "-1", "l3_entity": "-1"})
    if state is None:
        hass.states.async_remove("sensor.l1")
    else:
        hass.states.async_set("sensor.l1", state)
    aioclient_mock.post(URL, json={})
    await _send(hass, entry)
    assert aioclient_mock.call_count == 0
    assert "nicht verfügbar" in caplog.text or "unplausible Phasenspannung" in caplog.text

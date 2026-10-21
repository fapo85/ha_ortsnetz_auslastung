"""Optional standard fields and the collapsed additional measurements section."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers.data_entry_flow import FlowManagerIndexView
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ortsnetz_auslastung import _send
from custom_components.ortsnetz_auslastung.const import DOMAIN

URL = "https://example.test/v1/measurements"
SECTION = "additional_measurements"
PHASES = {"l1_entity": "sensor.l1", "l2_entity": "sensor.l2", "l3_entity": "sensor.l3"}
STANDARD = {"battery_soc_percent": (0, "%"), "grid_power_w": (-1250, "W")}
ADVANCED = {
    "power_factor": (0.98, None), "apparent_power_va": (1300, "VA"),
    "l1_a": (5.4, "A"), "l2_a": (0, "A"), "l3_a": (-1, "A"),
    **{f"l{phase}_v_{suffix}": (value, "V") for phase in (1, 2, 3)
       for suffix, value in (("min", 228), ("avg", 230), ("max", 232))},
    **{f"grid_frequency_hz_{suffix}": (value, "Hz")
       for suffix, value in (("min", 49.99), ("avg", 50), ("max", 50.01))},
}


def _entry(hass, measurements=None, capacity=None):
    data = {"api_url": URL, **PHASES, "latitude": 52.5, "longitude": 13.4}
    for phase in (1, 2, 3):
        hass.states.async_set(f"sensor.l{phase}", "230", {"unit_of_measurement": "V"})
    for field, (value, unit) in (measurements or {}).items():
        entity_id = f"sensor.{field}"
        hass.states.async_set(entity_id, str(value), {"unit_of_measurement": unit} if unit is not None else {})
        data[f"{field}_entity"] = entity_id
    if capacity is not None:
        data["battery_capacity"] = capacity
    entry = MockConfigEntry(domain=DOMAIN, version=3, data=data)
    entry.add_to_hass(hass)
    return entry


async def _payload(hass, aioclient_mock, entry):
    aioclient_mock.post(URL, json={})
    await _send(hass, entry)
    assert aioclient_mock.call_count == 1
    return aioclient_mock.mock_calls[0][2]


async def test_standard_fields_visible_and_additional_section_collapsed(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    fields = result["data_schema"].schema
    for field in ("battery_soc_percent_entity", "battery_capacity", "grid_power_w_entity"):
        key = next(key for key in fields if key == field)
        assert isinstance(key, vol.Optional)
        assert key.default is vol.UNDEFINED
    additional = fields[SECTION]
    assert additional.options["collapsed"] is True
    assert set(additional.schema.schema) == {f"{field}_entity" for field in ADVANCED}
    assert not set(additional.schema.schema) & set(fields)


async def test_configuration_can_be_rendered_by_the_frontend(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    rendered = FlowManagerIndexView(hass.config_entries.flow)._prepare_result_json(result)
    json.dumps(rendered)
    fields = {field["name"]: field for field in rendered["data_schema"]}
    assert fields[SECTION]["type"] == "expandable"
    assert fields[SECTION]["expanded"] is False
    assert len(fields[SECTION]["schema"]) == 17


@pytest.mark.parametrize("language", ["de", "en"])
def test_every_new_field_is_translated_in_setup_and_options(language):
    path = Path(__file__).parents[1] / "custom_components" / DOMAIN / "translations" / f"{language}.json"
    def unique_keys(pairs):
        result = dict(pairs)
        assert len(result) == len(pairs), "Duplicate translation key"
        return result
    translations = json.loads(path.read_text(), object_pairs_hook=unique_keys)
    for area, step in (("config", "user"), ("options", "init")):
        translated = translations[area]["step"][step]
        for name in ("battery_soc_percent_entity", "battery_capacity", "grid_power_w_entity"):
            assert "optional" in translated["data"][name]
        additional = translated["sections"][SECTION]
        assert set(additional["data"]) == {f"{field}_entity" for field in ADVANCED}
        assert all("optional" in label for label in additional["data"].values())


async def test_setup_flattens_additional_fields(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    with patch("custom_components.ortsnetz_auslastung.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {
            "api_url": URL, "phase_voltages": PHASES, "battery_capacity": 12.5,
            "battery_soc_percent_entity": "sensor.soc", "grid_power_w_entity": "sensor.grid_power",
            SECTION: {"power_factor_entity": "sensor.factor"},
        })
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["power_factor_entity"] == "sensor.factor"
    assert result["data"]["battery_capacity"] == 12.5
    assert SECTION not in result["data"]


@pytest.mark.parametrize("capacity", [0, -1, float("nan"), float("inf")])
async def test_setup_rejects_invalid_battery_capacity(hass, capacity):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    values = {"api_url": URL, "phase_voltages": PHASES, "battery_capacity": capacity}
    if capacity < 0:
        with pytest.raises(InvalidData):
            await hass.config_entries.flow.async_configure(result["flow_id"], values)
    else:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], values)
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"battery_capacity": "invalid_battery_capacity"}


async def test_all_twenty_optional_measurements_are_sent(hass, aioclient_mock):
    values = STANDARD | ADVANCED
    payload = await _payload(hass, aioclient_mock, _entry(hass, values, capacity=12.5))
    for field, (value, _) in values.items():
        assert payload[field] == value
    assert payload["battery_capacity"] == 12.5
    assert len(values) + 1 == 20


async def test_unconfigured_measurements_are_omitted(hass, aioclient_mock):
    payload = await _payload(hass, aioclient_mock, _entry(hass))
    assert not (STANDARD.keys() | ADVANCED.keys() | {"battery_capacity"}) & payload.keys()


@pytest.mark.parametrize(("field", "value", "unit", "expected"), [
    ("grid_power_w", -1.25, "kW", -1250),
    ("grid_power_w", 0, "W", 0),
    ("apparent_power_va", 1.3, "kVA", 1300),
    ("l1_a", 230, "mA", 0.23),
    ("power_factor", 98, "%", 0.98),
    ("power_factor", 0.98, "", 0.98),
    ("battery_soc_percent", 100, "%", 100),
    ("l1_v_min", -1, "V", -1),
])
async def test_units_and_valid_boundary_values(hass, aioclient_mock, field, value, unit, expected):
    payload = await _payload(hass, aioclient_mock, _entry(hass, {field: (value, unit)}))
    assert payload[field] == pytest.approx(expected)


@pytest.mark.parametrize(("field", "value", "unit"), [
    ("battery_soc_percent", -1, "%"), ("battery_soc_percent", 101, "%"),
    ("battery_soc_percent", "unavailable", "%"), ("battery_soc_percent", 50, "kWh"),
    ("grid_power_w", "nan", "W"), ("grid_power_w", "inf", "W"),
    ("grid_power_w", 1e308, "kW"), ("grid_power_w", 100, "kWh"),
    ("power_factor", -0.5, None), ("power_factor", 1.1, None), ("power_factor", 0.5, "W"),
    ("apparent_power_va", -1, "VA"), ("l1_a", -2, "A"),
    ("l1_v_min", 0, "V"), ("l1_v_max", 501, "V"),
    ("grid_frequency_hz_avg", 60, "Hz"), ("grid_frequency_hz_min", -1, "Hz"),
])
async def test_invalid_optional_value_does_not_block_voltages(hass, aioclient_mock, field, value, unit):
    payload = await _payload(hass, aioclient_mock, _entry(hass, {field: (value, unit)}))
    assert field not in payload
    assert payload["l1_v"] == 230


@pytest.mark.parametrize("capacity", [0, -1, float("nan"), float("inf")])
async def test_invalid_saved_capacity_is_omitted(hass, aioclient_mock, capacity):
    payload = await _payload(hass, aioclient_mock, _entry(hass, capacity=capacity))
    assert "battery_capacity" not in payload
    assert payload["l1_v"] == 230


async def test_inconsistent_partial_statistics_are_omitted(hass, aioclient_mock):
    payload = await _payload(hass, aioclient_mock, _entry(hass, {
        "l1_v_min": (240, "V"), "l1_v_avg": (230, "V"), "l2_v_min": (228, "V"),
    }))
    assert "l1_v_min" not in payload
    assert "l1_v_avg" not in payload
    assert payload["l2_v_min"] == 228


async def test_missing_phase_marker_is_ignored_for_statistics_order(hass, aioclient_mock):
    payload = await _payload(hass, aioclient_mock, _entry(hass, {
        "l1_v_min": (-1, "V"), "l1_v_avg": (230, "V"), "l1_v_max": (232, "V"),
    }))
    assert payload["l1_v_min"] == -1
    assert payload["l1_v_avg"] == 230


async def test_zero_apparent_power_omits_power_factor(hass, aioclient_mock):
    payload = await _payload(hass, aioclient_mock, _entry(hass, {
        "apparent_power_va": (0, "VA"), "power_factor": (0.98, None),
    }))
    assert payload["apparent_power_va"] == 0
    assert "power_factor" not in payload


async def test_options_restore_and_clear_new_fields(hass, aioclient_mock):
    entry = _entry(hass, STANDARD | ADVANCED, capacity=12.5)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    additional = result["data_schema"].schema[SECTION]
    assert additional.options["collapsed"] is True
    key = next(key for key in additional.schema.schema if key == "power_factor_entity")
    assert key.description["suggested_value"] == "sensor.power_factor"
    assert key.default is vol.UNDEFINED
    await hass.config_entries.options.async_configure(result["flow_id"], {
        "api_url": URL, "phase_voltages": PHASES,
    })
    payload = await _payload(hass, aioclient_mock, entry)
    assert not (STANDARD.keys() | ADVANCED.keys() | {"battery_capacity"}) & payload.keys()


async def test_options_keep_selected_additional_field(hass, aioclient_mock):
    entry = _entry(hass, ADVANCED)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(result["flow_id"], {
        "api_url": URL, "phase_voltages": PHASES,
        SECTION: {"power_factor_entity": "sensor.power_factor"},
    })
    payload = await _payload(hass, aioclient_mock, entry)
    assert payload["power_factor"] == 0.98
    assert "l1_a" not in payload

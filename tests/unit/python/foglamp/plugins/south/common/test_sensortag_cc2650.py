# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Unit test for foglamp.plugins.south.common.sensortag_cc2650.py"""

import pexpect
import pytest
import uuid
from unittest.mock import call, Mock
from foglamp.plugins.south.common import sensortag_cc2650
from foglamp.plugins.south.common.sensortag_cc2650 import SensorTagCC2650

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.fixture
def connection(mocker):
    con = mocker.patch.object(pexpect, "spawn", return_value=Mock(spec=pexpect.spawn))
    con.expect = Mock(return_value=1)
    return con


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "common", "sensortagcc2650")
class TestSensortagCc2650:
    def test___init__(self, mocker):
        # GIVEN
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        # WHEN
        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)

        # THEN
        assert isinstance(sensortag, SensorTagCC2650)
        assert sensortag.is_connected is True
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully')]
        log_debug.assert_has_calls(calls, any_order=True)

    def test___init__exception(self, mocker):
        # GIVEN
        log_exception = mocker.patch.object(sensortag_cc2650._LOGGER, "exception")
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug", side_effect=Exception())
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        # WHEN
        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)

        # THEN
        assert isinstance(sensortag, SensorTagCC2650)
        assert sensortag.is_connected is False
        log_debug.assert_called_once_with(
            'SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.')
        log_exception.assert_called_once_with(
            'SensorTagCC2650 B0:91:22:EA:79:04 connection failure. Timeout=10 seconds.')

    def test_disconnect(self, mocker):
        # GIVEN
        log_exception = mocker.patch.object(sensortag_cc2650._LOGGER, "exception")
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        log_error = mocker.patch.object(sensortag_cc2650._LOGGER, "error")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        # WHEN
        sensortag.disconnect()

        # THEN
        assert sensortag.is_connected is False
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 disconnected')]
        log_debug.assert_has_calls(calls, any_order=True)
        assert log_error.call_count is 0
        assert log_exception.call_count is 0

    def test_disconnect_error(self, mocker):
        # GIVEN
        log_exception = mocker.patch.object(sensortag_cc2650._LOGGER, "exception")
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug", side_effect=Exception())
        log_error = mocker.patch.object(sensortag_cc2650._LOGGER, "error")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is False

        # WHEN
        sensortag.disconnect()

        # THEN
        assert sensortag.is_connected is False
        log_debug.assert_called_once_with(
            'SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.')
        log_exception.assert_called_once_with(
            'SensorTagCC2650 B0:91:22:EA:79:04 connection failure. Timeout=10 seconds.')
        log_error.assert_called_once_with('SensorTagCC2650 B0:91:22:EA:79:04 not connected')

    def test_disconnect_exception(self, mocker):
        # GIVEN
        log_exception = mocker.patch.object(sensortag_cc2650._LOGGER, "exception")
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        con = mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        # WHEN
        attrs = {"sendline.return_value": 12, "sendline.side_effect": [Exception]}
        con.configure_mock(**attrs)
        sensortag.disconnect()

        # THEN
        assert sensortag.is_connected is True
        log_exception.assert_called_once_with('SensorTagCC2650 B0:91:22:EA:79:04 connection failure. ')
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully')]
        log_debug.assert_has_calls(calls)

    def test_get_char_handle(self, mocker):
        # GIVEN
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        con = mocker.patch.object(SensorTagCC2650, "con", return_value=p)
        mocker.patch.object(SensorTagCC2650, "_CHAR_HANDLE_TIMEOUT", 0.1)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        mocker.patch.object(con, "after",
                            b'handle: 0x003c 	 value: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')

        # WHEN
        retval = sensortag.get_char_handle(uuid.uuid4())

        # THEN
        assert "0x003c" == retval
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully')]
        log_debug.assert_has_calls(calls, any_order=True)

    def test_get_char_handle_exception(self, mocker):
        # GIVEN
        log_exception = mocker.patch.object(sensortag_cc2650._LOGGER, "exception")
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        con = mocker.patch.object(SensorTagCC2650, "con", return_value=p)
        mocker.patch.object(SensorTagCC2650, "_CHAR_HANDLE_TIMEOUT", 0.1)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        mocker.patch.object(con, "after",
                            b'handle: 0x003c 	 value: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00')
        mocker.patch.object(con, "expect", side_effect=Exception)

        # WHEN
        retval = sensortag.get_char_handle(uuid.uuid4())

        # THEN
        assert "0x0000" == retval
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully')]
        log_debug.assert_has_calls(calls, any_order=True)
        log_exception.assert_called_once_with('SensorTagCC2650 B0:91:22:EA:79:04 retrying fetching characteristics...')

    def test_get_notification_handles(self, mocker):
        # GIVEN
        log_info = mocker.patch.object(sensortag_cc2650._LOGGER, "info")
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        con = mocker.patch.object(SensorTagCC2650, "con", return_value=p)
        mocker.patch.object(SensorTagCC2650, "_NOTIFICATION_HANDLES_SLEEP", 0.1)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        mocker.patch.object(con, "after",
                            b'\nhandle: 0x001f 	 value: 00 00\nhandle: 0x0025 	 value: 00 00\nhandle: 0x002d 	 value: 00 00')

        # WHEN
        retval = sensortag.get_notification_handles()

        # THEN
        assert ['0x001f', '0x0025', '0x002d'] == retval
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully')]
        log_debug.assert_has_calls(calls, any_order=True)
        log_info.assert_called_once_with(
            'SensorTagCC2650 B0:91:22:EA:79:04 notification handles 0x001f, 0x0025, 0x002d')

    def test_get_notification_handles_exception(self, mocker):
        # GIVEN
        log_info = mocker.patch.object(sensortag_cc2650._LOGGER, "info")
        log_exception = mocker.patch.object(sensortag_cc2650._LOGGER, "exception")
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        con = mocker.patch.object(SensorTagCC2650, "con", return_value=p)
        mocker.patch.object(SensorTagCC2650, "_NOTIFICATION_HANDLES_SLEEP", 0.1)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        mocker.patch.object(con, "after",
                            b'\nhandle: 0x001f 	 value: 00 00\nhandle: 0x0025 	 value: 00 00\nhandle: 0x002d 	 value: 00 00')

        mocker.patch.object(con, "expect", side_effect=Exception)

        # WHEN
        retval = sensortag.get_notification_handles()

        # THEN
        assert [] == retval
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully')]
        log_debug.assert_has_calls(calls, any_order=True)
        assert 0 == log_info.call_count
        log_exception.assert_called_once_with('SensorTagCC2650 B0:91:22:EA:79:04 retrying notification handles...')

    def test_char_write_cmd(self, mocker):
        # GIVEN
        p = pexpect.spawn('cat', echo=False, timeout=5)
        con = mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        sendline = mocker.patch.object(con, "sendline")

        # WHEN
        sensortag.char_write_cmd(b'0x120', b'00')

        # THEN
        sendline.assert_called_once_with("char-write-cmd b'0x120' b'00'")

    def test_char_read_hnd(self, mocker):
        # GIVEN
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        con = mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        sendline = mocker.patch.object(con, "sendline")
        mocker.patch.object(con, "after",
                            b'Characteristic value/descriptor: 12 3c 00 00 00 00 00 00 00 00 b0 00 40 51 04 81 aa 00 f0')

        # WHEN
        retval = sensortag.char_read_hnd(b'0x120', "pressure")

        # THEN
        sendline.assert_called_once_with("char-read-hnd b'0x120'")
        assert b'510481aa00f0' == retval
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully'),
            call(
                "SensorTagCC2650 B0:91:22:EA:79:04 DEBUGGING: Reading from Tag... b'Characteristic value/descriptor: 12 3c 00 00 00 00 00 00 00 00 b0 00 40 51 04 81 aa 00 f0' \n"),
            call("SensorTagCC2650 B0:91:22:EA:79:04 type: pressure bytes: b'510481aa00f0'")]
        log_debug.assert_has_calls(calls, any_order=True)

    @pytest.mark.parametrize("sensortype, rawdata, log_msg", [
        ('temperature', b'81aa00f0', "SensorTagCC2650 B0:91:22:EA:79:04 type: temperature bytes: b'81aa00f0'"),
        ('movement', b'3c0000000000000000b00040510481aa00f0',
         "SensorTagCC2650 B0:91:22:EA:79:04 type: movement bytes: b'3c0000000000000000b00040510481aa00f0'"),
        ('humidity', b'81aa00f0', "SensorTagCC2650 B0:91:22:EA:79:04 type: humidity bytes: b'81aa00f0'"),
        ('pressure', b'510481aa00f0', "SensorTagCC2650 B0:91:22:EA:79:04 type: pressure bytes: b'510481aa00f0'"),
        ('luminance', b'00f0', "SensorTagCC2650 B0:91:22:EA:79:04 type: luminance bytes: b'00f0'"),
        ('battery', b'f0', "SensorTagCC2650 B0:91:22:EA:79:04 type: battery bytes: b'f0'"),
        ('error', 0, "SensorTagCC2650 B0:91:22:EA:79:04 type: error bytes: 0")
    ])
    def test_get_raw_measurement(self, sensortype, rawdata, log_msg, mocker):
        # GIVEN
        reading = [b'12', b'3c', b'00', b'00', b'00', b'00', b'00', b'00', b'00', b'00', b'b0', b'00',
                   b'40', b'51', b'04', b'81', b'aa', b'00', b'f0']
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        # WHEN
        retval = sensortag.get_raw_measurement(sensortype, reading)

        # THEN
        assert rawdata == retval
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully'),
            call(log_msg)]
        log_debug.assert_has_calls(calls, any_order=True)

    def test_hex_temp_to_celsius(self, mocker):
        # GIVEN
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        reading = b'81aa00f0'

        # WHEN
        retval = sensortag.hex_temp_to_celsius(reading)

        # THEN
        assert (341.0, 480.0) == retval
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 object: 341.0 ambient: 480.0')]
        log_debug.assert_has_calls(calls, any_order=True)

    def test_hex_movement_to_movement(self, mocker):
        # GIVEN
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        reading = b'3c0000000000000000b00040510481aa00f0'

        # WHEN
        retval = sensortag.hex_movement_to_movement(reading)

        # THEN
        assert (0.457763671875, 0.0, 0.0, 0.0, -5.0, 4.0,
                165.68253968253967, -3281.7137973137974, -614.1499389499389, 2) == retval
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully'),
            call(
                'SensorTagCC2650 B0:91:22:EA:79:04 g: 0.457763671875 0.0 0.0 a: 0.0 -5.0 m: 4.0 165.68253968253967 -3281.7137973137974, ar: -614.1499389499389')]
        log_debug.assert_has_calls(calls, any_order=True)

    def test_hex_humidity_to_rel_humidity(self, mocker):
        # GIVEN
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        reading = b'81aa00f0'

        # WHEN
        retval = sensortag.hex_humidity_to_rel_humidity(reading)

        # THEN
        assert (93.75, 69.89509582519531) == retval
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 humidity: 93.75 temperature: 69.89509582519531')]
        log_debug.assert_has_calls(calls, any_order=True)

    def test_hex_pressure_to_pressure(self, mocker):
        # GIVEN
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        reading = b'510481aa00f0'

        # WHEN
        retval = sensortag.hex_pressure_to_pressure(reading)

        # THEN
        assert 157288.1 == retval
        calls = [call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
                 call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully'),
                 call('SensorTagCC2650 B0:91:22:EA:79:04 pressure: 157288.1')]
        log_debug.assert_has_calls(calls, any_order=True)

    def test_hex_lux_to_lux(self, mocker):
        # GIVEN
        log_debug = mocker.patch.object(sensortag_cc2650._LOGGER, "debug")
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        reading = b'00f0'

        # WHEN
        retval = sensortag.hex_lux_to_lux(reading)

        # THEN
        assert 0.0 == retval
        calls = [
            call('SensorTagCC2650 B0:91:22:EA:79:04 Connecting... If nothing happens, please press the power button.'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 connected successfully'),
            call('SensorTagCC2650 B0:91:22:EA:79:04 luminance: 0.0')]
        log_debug.assert_has_calls(calls, any_order=True)

    def test_get_battery_level(self, mocker):
        # GIVEN
        p = pexpect.spawn('cat', echo=False, timeout=5)
        mocker.patch.object(SensorTagCC2650, "con", return_value=p)

        sensortag = SensorTagCC2650("B0:91:22:EA:79:04", 10)
        assert sensortag.is_connected is True

        reading = b'f0'

        # WHEN
        retval = sensortag.get_battery_level(reading)

        # THEN
        assert 240 == retval

    @pytest.mark.skip(reason="Not implemented")
    def test_get_keypress_state(self, mocker):
        pass

# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pytest
import foglamp.services.common.avahi as avahi

def test_byte_array_to_string():
    array = [104,101,108,108,111]
    str = avahi.byte_array_to_string(array)
    assert str == 'hello'

def test_byte_array_to_string_unprintable():
    array = [104,101,108,108,111,12]
    str = avahi.byte_array_to_string(array)
    assert str == 'hello.'

def test_txt_array_string_array():
    a1 = [104,101,108,108,111]
    a2 = [104,101,108,108,111]
    strs = avahi.txt_array_to_string_array([a1, a2])
    assert strs[0] == 'hello'
    assert strs[1] == 'hello'

def test_string_to_byte_array():
    array = avahi.string_to_byte_array('hello')
    assert array[0] == 104
    assert array[1] == 101
    assert array[2] == 108
    assert array[3] == 108
    assert array[4] == 111

def test_string_array_to_txt_array():
    arrays = avahi.string_array_to_txt_array(['hello','hello'])
    array = arrays[0]
    assert array[0] == 104
    assert array[1] == 101
    assert array[2] == 108
    assert array[3] == 108
    assert array[4] == 111
    array = arrays[1]
    assert array[0] == 104
    assert array[1] == 101
    assert array[2] == 108
    assert array[3] == 108
    assert array[4] == 111

def test_dict_to_txt_array():
    dict = { "hello" : "world" }
    arrays = avahi.dict_to_txt_array(dict)
    array = arrays[0]
    assert array[0] == 104
    assert array[1] == 101
    assert array[2] == 108
    assert array[3] == 108
    assert array[4] == 111
    assert array[5] == 61
    assert array[6] == 119
    assert array[7] == 111
    assert array[8] == 114
    assert array[9] == 108
    assert array[10] == 100

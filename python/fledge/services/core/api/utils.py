# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import subprocess
import os
import json
from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_PLUGIN_PATH
from fledge.common.logger import FLCoreLogger

_logger = FLCoreLogger().get_logger(__name__)
_lib_path = _FLEDGE_ROOT + "/" + "plugins"

C_PLUGIN_UTIL_PATH = _FLEDGE_ROOT + "/extras/C/get_plugin_info" if os.path.isdir(_FLEDGE_ROOT + "/extras/C") \
        else _FLEDGE_ROOT + "/cmake_build/C/plugins/utils/get_plugin_info"


def get_plugin_info(name, dir):
    try:
        arg2 = _find_c_lib(name, dir)
        if arg2 is None:
            raise ValueError('The plugin {} does not exist'.format(name))
        cmd_with_args = [C_PLUGIN_UTIL_PATH, arg2, "plugin_info"]
        p = subprocess.Popen(cmd_with_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        res = out.decode("utf-8")
        jdoc = json.loads(res)
    except (OSError, ValueError) as err:
        _logger.error(err, "{} C plugin get info failed.".format(name))
        return {}
    except subprocess.CalledProcessError as err:
        if err.output is not None:
            _logger.error(err, "{} C plugin get info failed '{}'.".format(name, err.output))
        else:
            _logger.error(err, "{} C plugin get info failed.".format(name))
        return {}
    except Exception as ex:
        _logger.error(ex, "{} C plugin get info failed.".format(name))
        return {}
    else:
        return jdoc


def _find_c_lib(name, installed_dir):
    _path = [_lib_path + "/" + installed_dir]
    _path = _find_plugins_from_env(_path)
    lib_path = None

    for fp in _path:
        for path, subdirs, files in os.walk(fp):
            for fname in files:
                # C-binary file
                if fname.endswith("lib{}.so".format(name)):
                    lib_path = os.path.join(path, fname)
                    break
            else:
                continue
            break
    return lib_path


def find_c_plugin_libs(direction):
    libraries = []
    _path = [_lib_path]
    _path = _find_plugins_from_env(_path)
    for fp in _path:
        if os.path.isdir(fp + "/" + direction):
            for name in os.listdir(fp + "/" + direction):
                p = fp + "/" + direction + "/" + name
                for fname in os.listdir(p):
                    if fname.endswith('.so'):
                        # Replace lib and .so from fname
                        libraries.append((fname.replace("lib", "").replace(".so", ""), 'binary'))
                    # For Hybrid plugins
                    if direction == 'south' and fname.endswith('.json'):
                        libraries.append((fname.replace(".json", ""), 'json'))
    return libraries


def _find_plugins_from_env(_plugin_path: list) -> list:
    if _FLEDGE_PLUGIN_PATH:
        my_list = _FLEDGE_PLUGIN_PATH.split(";")
        for ml in my_list:
            dir_found = os.path.isdir(ml)
            if dir_found:
                subdirs = [dirs for x, dirs, files in os.walk(ml)]
                if subdirs[0]:
                    _plugin_path.append(ml)
                else:
                    _logger.warning("{} subdir type not found.".format(ml))
            else:
                _logger.warning("{} dir path not found.".format(ml))
    return _plugin_path

# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END


import subprocess
import os
import json

from fledge.common import logger
from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_PLUGIN_PATH

_logger = logger.setup(__name__)
_lib_path = _FLEDGE_ROOT + "/" + "plugins"


def get_plugin_info(name, dir):
    try:
        arg1 = _find_c_util('get_plugin_info')
        arg2 = _find_c_lib(name, dir)
        if arg2 is None:
            raise ValueError('The plugin {} does not exist'.format(name))
        cmd_with_args = [arg1, arg2, "plugin_info"]
        p = subprocess.Popen(cmd_with_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        res = out.decode("utf-8")
        jdoc = json.loads(res)
    except OSError as err:
        _logger.error("%s C plugin get info failed due to %s", name, str(err))
        return {}
    except subprocess.CalledProcessError as err:
        if err.output is not None:
            _logger.error("%s C plugin get info failed '%s' due to %s", name, err.output, str(err))
        else:
            _logger.error("%s C plugin get info failed due to %s", name, str(err))
        return {}
    except ValueError as err:
        _logger.error(str(err))
        return {}
    except Exception as ex:
        _logger.exception("%s C plugin get info failed due to %s", name, str(ex))
        return {}
    else:
        return jdoc


def _find_c_lib(name, dir):
    _path = [_lib_path + "/" + dir]
    _path = _find_plugins_from_env(_path)
    for fp in _path:
        for path, subdirs, files in os.walk(fp):
            for fname in files:
                # C-binary file
                if fname.endswith(name + '.so'):
                    return os.path.join(path, fname)
    return None


def _find_c_util(name):
    for path, subdirs, files in os.walk(_FLEDGE_ROOT):
        for fname in files:
            # C-utility file
            if fname == name:
                return os.path.join(path, fname)
    return None


def find_c_plugin_libs(direction):
    libraries = []
    _path = [_lib_path]
    _path = _find_plugins_from_env(_path)
    for fp in _path:
        for root, dirs, files in os.walk(fp + "/" + direction):
            for name in dirs:
                p = os.path.join(root, name)
                for path, subdirs, f in os.walk(p):
                    for fname in f:
                        # C-binary file
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
        for l in my_list:
            dir_found = os.path.isdir(l)
            if dir_found:
                subdirs = [dirs for x, dirs, files in os.walk(l)]
                if subdirs[0]:
                    _plugin_path.append(l)
                else:
                    _logger.warning("{} subdir type not found".format(l))
            else:
                _logger.warning("{} dir path not found".format(l))
    return _plugin_path

import subprocess
import os
import json
from foglamp.common import logger
from foglamp.common.common import _FOGLAMP_ROOT

_logger = logger.setup(__name__)
_lib_path = _FOGLAMP_ROOT + "/" + "plugins"


def get_plugin_info(name):
    try:
        arg1 = _find_c_util('get_plugin_info')
        arg2 = _find_c_lib(name)
        cmd_with_args = [arg1, arg2, "plugin_info"]
        p = subprocess.Popen(cmd_with_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        res = out.decode("utf-8")
        jdoc = json.loads(res)
    except (OSError, subprocess.CalledProcessError, Exception) as ex:
        _logger.exception("%s C plugin get info failed due to %s", name, ex)
        return {}
    else:
        return jdoc


def _find_c_lib(name):
    for path, subdirs, files in os.walk(_lib_path):
        for fname in files:
            # C-binary file
            if fname.endswith(name + '.so'):
                return os.path.join(path, fname)
    return None


def _find_c_util(name):
    for path, subdirs, files in os.walk(_FOGLAMP_ROOT):
        for fname in files:
            # C-utility file
            if fname == name:
                return os.path.join(path, fname)
    return None


def find_c_plugin_libs(direction):
    libraries = []
    for root, dirs, files in os.walk(_lib_path + "/" + direction):
        for name in dirs:
            p = os.path.join(root, name)
            for path, subdirs, f in os.walk(p):
                for fname in f:
                    # C-binary file
                    if fname.endswith('.so'):
                        # Replace lib and .so from fname
                        libraries.append(fname.replace("lib", "").replace(".so", ""))
    return libraries

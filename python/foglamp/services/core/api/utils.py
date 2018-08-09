import subprocess
import os
import json
from foglamp.common import logger
from foglamp.common.common import _FOGLAMP_ROOT

_logger = logger.setup(__name__)


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
        _logger.exception("C plugin get info failed due to %s", ex)
        return {}
    else:
        return jdoc


def _find_c_lib(name):
    for path, subdirs, files in os.walk(_FOGLAMP_ROOT):
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
    # FIXME: Duplicate binaries found only in case "make",
    # follow_links=False by default in os.walk() should ignore such symbolic links but right now its not working
    for root, dirs, files in os.walk(_FOGLAMP_ROOT, followlinks=False):
        for name in dirs:
            if 'plugins' in name:
                p = os.path.join(root, name) + "/" + direction
                for path, subdirs, f in os.walk(p):
                    for fname in f:
                        # C-binary file
                        if fname.endswith('.so'):
                            # Replace lib and .so from fname
                            libraries.append(fname.replace("lib", "").replace(".so", ""))
    return libraries

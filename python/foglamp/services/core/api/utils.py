import subprocess
import os
import json
from foglamp.common import logger
from foglamp.common.common import _FOGLAMP_ROOT

_logger = logger.setup(__name__)


def get_plugin_info(name):
    try:
        arg1 = find_C_libs_and_utils('get_plugin_info')
        arg2 = find_C_libs_and_utils(name)

        cmd_with_args = [arg1, arg2, "plugin_info"]
        p = subprocess.Popen(cmd_with_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        res = out.decode("utf-8")
        jdoc = json.loads(res)
    except (OSError, subprocess.CalledProcessError, Exception) as ex:
        _logger.exception("C Plugin get info failed due to {}".format(str(ex)))
        return {}
    else:
        return jdoc


def find_C_libs_and_utils(name):
    for path, subdirs, files in os.walk(_FOGLAMP_ROOT):
        for fname in files:
            # C-binary file
            if fname.endswith(name + '.so'):
                return os.path.join(path, fname)
            # C-utility file
            if fname == name:
                return os.path.join(path, fname)


def find_C_plugin_folders(direction):
    directories = []
    for root, dirs, files in os.walk(_FOGLAMP_ROOT, topdown=False):
        for name in dirs:
            if 'plugins' in dirs:
                p = os.path.join(root, name) + "/" + direction
                for path, subdirs, f in os.walk(p):
                    for fname in f:
                        # C-binary file
                        if fname.endswith('.so'):
                            # Split directory with /direction/
                            c = path.split("/" + direction + "/")
                            # TODO: Duplicate binaries found only in case "make"
                            directories.append(c[1])
    return directories

import subprocess
import os
import json
from foglamp.common import logger
from foglamp.common.common import _FOGLAMP_ROOT

_logger = logger.setup(__name__)


def get_plugin_info(direction, name):
    try:
        # make
        if os.path.isdir(_FOGLAMP_ROOT + '/cmake_build'):
            arg1 = "cmake_build/C/plugins/utils/get_plugin_info"
            arg2 = "cmake_build/C/plugins/{}/{}/lib{}.so".format(direction, name, name)
        else:
            # sudo make install
            arg1 = "extras/C/get_plugin_info"
            arg2 = "plugins/{}/{}/lib{}.so".format(direction, name, name)

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
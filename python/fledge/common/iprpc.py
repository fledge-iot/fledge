# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" interprocess rpc """


__author__ = "Douglas Orr"
__copyright__ = "Copyright (c) 2020 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


import os
import sys
import io
import subprocess
import threading
import pickle
import tempfile
import time
import logging
import mmap


sys.path.append(os.path.dirname(__file__))
DEBUG_RPC = os.environ.get('DEBUG_RPC', "false").lower() == "true"

try:
    from fledge.common import logger
except ImportError:
    # if invoked outside of fledge, fake up a logger environment
    class Logger:
        def __init__(self):
            self.CONSOLE = 0
            self.SYSLOG = 1
            self.default_destination = self.CONSOLE
            
        def setup(self, name, level):
            _logger = logging.getLogger(name)
            _logger.setLevel(level)
            return _logger
    logger = Logger()

_LOGGER = logger.setup(__name__, level=logging.INFO)


def eprint(*args, **kwargs):
    print(*args, *kwargs, file=sys.stderr)
    

def is_server_process():
    # temp backward compatibility: if we have a default
    # destination of SYSLOG, we are a server process
    return not hasattr(logger, 'default_destination') or \
        (logger.default_destination == logger.SYSLOG)
#
#
# IPC overview:
#   The basic structure we have is a client which spawns a server in another process, then
# do simple ipc to send procedure calls from client to server, then results back to client
#
# InterProcessRPC is spawned with a pipe to the client. Writes and reads on the pipe are used to
# synchronize work that is done in the server. Servers are required to be single threaded.
#
# The basic mechanism is to send a newline-terminated "length" to the server which signals
# new method/arguments are available. (In a pure-pipe implementation, the length precedes
# a "length"-sized encoded dict. In mapped file implementation, the "length" is merely
# used for signaling.)
#
# Arguments are sent in an encoded dict: {'method': <method-name>, 'args': <list of arguments>}
#
# In the mapped file implementation, there is a tmpfile of ARGFILE_SIZE mapped into client and
# server where the arguments are written using pickle. Results are written back the same way.
#
# For the process receiving the results, the length indicates a couple of special things:
# >0 -> standard dict
# =0 -> None
# <0 -> exception, which is re-constituted and re-raised, so the client receives it
#
# Argfile is a temp file (mkstemp) which is created by the client. The name is sent
# to the server as the first pipe message; it is opened and unlinked once opened so
# that it will disappear on close.
#
# The InterProcessRPCClient class will invoke a subprocess to create the server. Special
# care is taken to read stderr if the client is a server, so that error messages written to
# stderr (usually before the server starts) aren't lost.
#
# The IPCModuleClient derives from InterProcessRPCClient and  specifically
# invokes a named python module as a server.


ARGFILE_SIZE = 1024*1024*20


class InterProcessRPC:
    def __init__(self,
                 infd=io.BufferedReader(io.FileIO(os.dup(sys.stdin.fileno()))),
                 outfd=io.BufferedWriter(io.FileIO(os.dup(sys.stdout.fileno()), mode='w')),
                 errfd=sys.stderr,
                 name="",
                 argfile_fd=None):
        self.infd = infd    # for direct i/o between client/server
        self.outfd = outfd

        self.errfd = errfd
        self.name = name

        if argfile_fd is None:
            # server
            # close 0/1/2 in case client is trying to do i/o on them. use stderr for output
            os.close(0)
            os.close(1)
            os.dup2(2, 1)

            # special protocol for server process: first line read is the name of our mapped arg file
            _argfile_name = self.infd.readline()[:-1].decode('utf-8')
            self.argfile_fd = os.open(_argfile_name, os.O_RDWR)
            os.unlink(_argfile_name)  # delete on close
        else:
            # client process opens the file then passes it up to superclass
            self.argfile_fd = argfile_fd

        self.mfile = mmap.mmap(self.argfile_fd, ARGFILE_SIZE)  # assume input > output

    def call(self, rpcobj):
        """ call - local instance of rpc call """
        if not ('method' in rpcobj and 'args' in rpcobj):
            _LOGGER.error("invalid rpc object missing fields {}".format(str(rpcobj.keys())))
            raise ValueError

        _method = getattr(self, rpcobj['method'])
        _args = rpcobj['args']
        return _method(*_args)

    def rpc_read(self):
        """ rpc_read - read len/buf from the remote host
        protocol:
        each call is preceded by an ascii - <len>\n
          len == '' : EOF from remote side
          len > 0   : len sized buffer with json method + args follows
          len == 0  : None
          len < 0   : len sized buffer with named exception plus arg follows
        Returns:
            json dict if method or exception
            None if len == 0
        Raises:
            EOFError if pipe closes
        """

        # protocol: pipe produces a length of next object
        _len = self.infd.readline()  # assume small enough to not deadlock
        self.mfile.seek(0)

        if _len == b'':
            # closed fd on one side or the other of the pipe
            raise EOFError

        _len = int(_len)
        if _len > 0:
            # len > 0 -> json object

            # eprint("read >0")
            obj = pickle.loads(self.mfile)
            return obj

        elif _len < 0:
            # _len < 0 -> Exception
            _ex = pickle.loads(self.mfile)

            # reconstitute the exception, pass server exception through locally
            _ex_class, _ex_msg = _ex['class'], _ex['message']
            _builtins = globals()['__builtins__']
            if _ex_class in _builtins:
                raise _builtins[_ex_class](_ex_msg)

            # raise unknown exception
            _LOGGER.warning("unknown local exception {}".format(_ex_class))
            raise Exception("{}: {}".format(_ex_class, _ex_msg))

        # we fall through here when len == 0 -> None
        return None

    def rpc_write(self, obj, is_exception=False):
        """ rpc_write -- write an rpc return value to the receiver 
        protocol:
        each call is preceded by an ascii - <len>\n
          len > 0   : len sized buffer with json method + args follows
          len == 0  : None
          len < 0   : len sized buffer with named exception plus arg follows
        Returns:
        Raises:
        """

        _lenmult = 1
        if is_exception:
            # replace exception object with something that can be turned into JSON
            _class = obj.__class__.__name__
            obj = { 'class': str(_class), 'message': str(obj) }
            _lenmult = -1

        if obj is not None:
            # put the dict into shared memory
            self.mfile.seek(0)
            pickle.dump(obj, self.mfile)

            # write a leading "len", positive (object) or negative (exception)
            # and signal to the server there's something to do
            _lenstr = str(_lenmult * 1)+'\n'
            self.outfd.write(_lenstr.encode('utf-8', 'ignore'))
        else:
            # no payload for None return
            # eprint("rpc write none")
            _lenstr = '0\n'
            self.outfd.write(_lenstr.encode('utf-8', 'ignore'))

        self.outfd.flush()

    def rpc_exception(self, ex):
        """ exception -- write an exception object to client to represent internal error """

        # exception sent so that it will be raised in client
        self.rpc_write(ex, is_exception=True)

    def serve(self):
        """ receive "methods" to invoke on infd, return results on outfd

        each method is represented using (string) len followed by "len" worth of JSON packet
        JSON input packet is {method: methodname, args: args}

        return values and exceptions are written back on outfd in the same format; 

        . None returns have a zero length and are not JSON
        . Exceptions are JSON objects with exception type and message, and have a negative length
        . A length which is null string indicates closed channel
        """

        while True:
            try:
                _obj = self.rpc_read()
            except EOFError as ex:
                break
            except Exception as ex:
                self.rpc_exception(ex)

            try:
                _ret = self.call(_obj)  # local "call" - returns json-able value; may raise

            except Exception as ex:
                if DEBUG_RPC and type(ex) not in [EOFError, SystemExit]:
                    # give a traceback
                    _LOGGER.exception("exception in rpc backend")

                # return the exception
                self.rpc_exception(ex)

                if type(ex) is SystemExit:
                    _LOGGER.info("EXITING")
                    break

            else:
                # return the result of the call
                self.rpc_write(_ret)

        sys.exit()


class InterProcessRPCClient(InterProcessRPC):
    """
    InterProcessRPCClient: companion to InterProcessRPC, client code that calls into a server in a separate process
    """

    def __init__(self, server_args, env=None):

        # trap and send stderr to syslog if we are in a server process
        _is_server = is_server_process()
        _stderr = subprocess.PIPE if _is_server else None

        # set up a big shared memory file for argument transfer
        (_argfile_fd, _argfile_path) = tempfile.mkstemp()
        os.pwrite(_argfile_fd, b' ', ARGFILE_SIZE-1)

        p = subprocess.Popen(server_args,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=_stderr,
                             env=env)
        super().__init__(infd=p.stdout, outfd=p.stdin, errfd=p.stderr, argfile_fd=_argfile_fd)

        if _is_server:
            def log_errors(fd):
                """ log_errors - vacuum up error output that would otherwise be lost """
                while True:
                    err_str = fd.read().decode('utf-8')  # blocking read for error output
                    if err_str == '':
                        break
                    _LOGGER.error("python module error: {}".format(err_str))
                return

            # pull off and log errors that would disappear on stderr
            self.log_err_thread = threading.Thread(target=log_errors, args=(self.errfd,))
            self.log_err_thread.start()

        # check for module immediate exit -- shouldn't happen
        for _ in range(2):
            # Wait until process terminates (without using p.wait())
            if p.poll() is not None:
                _LOGGER.error("{} module load exited with return code {}".format(server_args, p.returncode))
                raise RuntimeError(p.returncode)
            # Process hasn't exited yet, let's wait some
            time.sleep(0.5)

        # special prtocol, now tell the server the name of the mapped arg file
        self.outfd.write('{}\n'.format(_argfile_path).encode('utf-8'))

    def call(self, rpcobj):
        """ call - rpc client writes rpc request, reads and returns the result 
        Args:
            rpcobj : dict() with:
            'method': name of remote method to invoke
            'args': JSON-able list of arguments to be sent to remote object
        Returns:
            de-JSON-ified return result from remote execution
        Raises:
            Exception with appropriate message raised in remote execution (xxx -- reinstantiate exception class)
        """
        self.rpc_write(rpcobj)
        return self.rpc_read()


class IPCModuleClient(InterProcessRPCClient):
    """ IPCModuleClient - specifically invoke python to create a server from a python module """
    def __init__(self, module_name, module_dir):

        env = os.environ.copy()
        # make sure the new environment can find modules in cwd
        env['PYTHONPATH'] = env.get('PYTHONPATH', '') + ":"+module_dir

        _LOGGER.debug("STARTING module {} path={}".format(module_name, env['PYTHONPATH']))
        super().__init__(['python3', '-m', module_name], env=env)

    def __getattr__(self, method_name):
        """ __getattr__  - override getattr so that we can proxy function calls by name """

        # NOTE: this is a dangerous game since we are comandeering all function/slot accesses
        # it's also not the most efficient thing in the world... but we're about to do a pipe rpc
        # so it's probalby also not the weakest link

        _super = super() # bind super outside of the lambda
        return lambda *x: _super.call({'method': method_name, 'args': [*x]})

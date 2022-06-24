# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Module for applying network impairments."""


__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# References
# 1. http://myconfigure.blogspot.com/2012/03/traffic-shaping.html
# 2. https://lartc.org/howto/lartc.qdisc.classful.html
# 3. https://lartc.org/howto/lartc.qdisc.filters.html
# 4. https://serverfault.com/a/841865
# 5. https://serverfault.com/a/906499
# 6. https://wiki.linuxfoundation.org/networking/netem
# 7. https://srtlab.github.io/srt-cookbook/how-to-articles/using-netem-to-emulate-networks/
# 8. https://wiki.linuxfoundation.org/networking/netem

import subprocess
import multiprocessing
import datetime
import time
import socket


def check_for_interface(interface):
    """Checks for given interface if present in output of ifconfig"""
    for tup in socket.if_nameindex():
        if tup[1] == interface:
            return True

    return False


class Distortion(multiprocessing.Process):
    def __init__(self, run_cmd_list, clear_cmd, duration):
        super(Distortion, self).__init__()
        self.run_cmd_list = run_cmd_list
        self.duration = duration
        self.clear_cmd = clear_cmd

    @staticmethod
    def run_command(command):
        """Executes a shell command using subprocess module."""
        try:
            process = subprocess.Popen(command, cwd=None, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        except Exception as inst:
            print("Problem running command : \n   ", str(command))
            return False

        [stdoutdata, stderrdata] = process.communicate(None)
        if process.returncode:
            print(stderrdata)
            print("Problem running command : \n   ", str(command), " ", process.returncode)
            return False

        return True

    def run(self) -> None:

        # Make sure we are in clean state. Ignore error if there.
        _ = Distortion.run_command(self.clear_cmd)

        for run_cmd in self.run_cmd_list:
            print("Executing {}".format(run_cmd), flush=True)
            ret_val = Distortion.run_command(run_cmd)
            if not ret_val:
                print("Could not perform execution of command {}".format(run_cmd), flush=True)
                return

        end_time = datetime.datetime.now() + datetime.timedelta(seconds=self.duration)
        while datetime.datetime.now() < end_time:
            time.sleep(0.5)

        print("Executing {}".format(self.clear_cmd), flush=True)
        ret_val = Distortion.run_command(self.clear_cmd)
        if not ret_val:
            print("Could not perform execution of command {}".format(self.clear_cmd), flush=True)
            return

        print("Network Impairment complete.", flush=True)


def reset_network(interface):
    """
    Reset the network in the middle of impairment.
    :param interface: The interface of the network.
    :type interface: string
    :return: True/False If successful.
    :rtype: boolean
    """
    if not check_for_interface(interface):
        raise Exception("Could not find given {} among present interfaces.".format(interface))

    clear_cmd = "sudo tc qdisc del dev {} root".format(interface)
    ret_val = Distortion.run_command(command=clear_cmd)

    if ret_val:
        print("Network has been reset.")
    else:
        print("Could not reset the network.")


def distort_network(interface, duration, rate_limit, latency, ip=None, port=None,
                    traffic=''):
    """

    :param interface: Interface on which network impairment will be applied. See ifconfig in
                       your linux machine to decide.
    :type interface: string
    :param duration: The duration (in seconds) for which impairment will be applied. Note it will
                     get auto cleared after application.
    :type duration: integer
    :param traffic:  If inbound then the given ip and port will be used to filter packets coming
                     from destination. For these packets only the impairment will be applied.
                     If outbound then we are talking about packets leaving this machine for destination.
                     This is exactly the opposite of first case.
    :type traffic:  inbound/ outbound string
    :param ip: The ip of machine where packets are coming / leaving to filter. Keep None
               if no filter required.
    :type ip: string
    :param port: The port of machine where packets are coming / leaving to filter.  Keep None
               if no filter required.
    :type port: integer
    :param rate_limit: The restriction in rate in kbps. Use value 20 for 20 kbps.
    :type rate_limit: integer
    :param latency: The delay to cause for every packet leaving/ coming from machine in
                    milliseconds. Use something like 300 for causing a delay for 300 milliseconds.
    :type latency: integer
    :return: None
    :rtype: None
    """

    if not check_for_interface(interface):
        raise Exception("Could not find given {} among present interfaces.".format(interface))

    if not latency and not rate_limit:
        raise Exception("Could not find latency or  rate_limit.")

    if latency:
        latency_converted = str(latency) + 'ms'
    else:
        latency_converted = None

    if rate_limit:
        rate_limit_converted = str(rate_limit) + 'Kbit'
    else:
        rate_limit_converted = None

    if not (ip and port):
        if rate_limit_converted and latency_converted:
            run_cmd = "sudo tc qdisc add dev {} root netem" \
                      " delay {} rate {}".format(interface, latency_converted,
                                                 rate_limit_converted)
        elif rate_limit_converted and not latency_converted:
            run_cmd = "sudo tc qdisc add dev {} root netem" \
                      " rate {}".format(interface, rate_limit_converted)
        elif not rate_limit_converted and latency_converted:
            run_cmd = "sudo tc qdisc add dev {} root netem" \
                      "delay {}".format(interface, latency_converted)

        clear_cmd = "sudo tc qdisc del dev {} root".format(interface)
        p = Distortion([run_cmd], clear_cmd, duration)
        p.daemon = True
        p.start()

    else:
        r1 = "sudo tc qdisc add dev {} root handle 1: prio" \
             " priomap 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2".format(interface)
        if latency_converted and rate_limit_converted:
            r2 = "sudo tc qdisc add dev {} parent 1:1 " \
                 "handle 10: netem delay {} rate {}".format(interface,
                                                            latency_converted,
                                                            rate_limit_converted)
        elif not latency_converted and rate_limit_converted:
            r2 = "sudo tc qdisc add dev {} parent 1:1 " \
                 "handle 10: netem  rate {}".format(interface,
                                                    rate_limit_converted)
        elif latency_converted and not rate_limit_converted:
            r2 = "sudo tc qdisc add dev {} parent 1:1 " \
                 "handle 10: netem delay {} ".format(interface,
                                                     latency_converted)

        if traffic.lower() == 'outbound':
            ip_param = 'dst'
            port_param = 'dport'

        elif traffic.lower() == "inbound":
            ip_param = 'src'
            port_param = 'sport'
        else:
            raise Exception("For ip and port are given then traffic has to be either inbound or outbound."
                            " But got other than these two. ")

        r3 = "sudo tc filter add dev {} protocol ip parent 1:0 prio 1 u32 " \
             "match ip {} {}/32 match ip {} {}  0xffff flowid 1:1".format(interface, ip_param,
                                                                          ip, port_param, port)
        clear_cmd = "sudo tc qdisc del dev {} root".format(interface)
        run_cmd_list = [r1, r2, r3]
        p = Distortion(run_cmd_list, clear_cmd, duration)
        p.daemon = True
        p.start()


""" -------------------------Usage -------------------------------------"""

# from network_impairment import distort_network, reset_network
# distort_network(interface="wlp2s0", duration=40, rate_limit=20, latency=300,
#                 ip="192.168.1.80", port=8081, traffic="inbound")
#
# distort_network(interface="wlp2s0", duration=40, rate_limit=20, latency=300,
#                 ip="192.168.1.80", port=8081, traffic="outbound")
#
# distort_network(interface="wlp2s0", duration=40, rate_limit=20, latency=300)

# reset_network(interface="wlp2s0")

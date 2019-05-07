#!/bin/sh

op=$(lsb_release -ds 2>/dev/null || cat /etc/*release 2>/dev/null | head -n1 || uname -om)
echo $op | egrep -q '(Red Hat|CentOS)'

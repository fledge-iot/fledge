#!/bin/bash

##--------------------------------------------------------------------
## Copyright (c) 2017 OSIsoft, LLC
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##--------------------------------------------------------------------

##
## write_log
## This script is used to write in the syslog and to echo output to stderr
## and stdout

#set -x

# Fetch environment variables for remote syslog configuration
SYSLOG_UDP_ENABLED=${SYSLOG_UDP_ENABLED:-false} # Enable/disable remote syslog (default: false)
LOG_IP=${LOG_IP:-"127.0.0.1"}                   # Remote syslog server IP (default: localhost)
LOG_PORT=${LOG_PORT:-5140}                       # Remote syslog server port (default: 514)
## The Loggging Handler
#
# Paramaters: $1 - Module
#             $2 - Function
#             $3 - Severity:
#                  - debug
#                  - info
#                  - notice
#                  - err
#                  - crit
#                  - alert
#                  - emerg
#             $4 - Message
#             $5 - Output:
#                  - logonly : send the message only to syslog
#                  - all     : send the message to syslog and stdout
#                  - outonly " send the message only to stdout
#             $6 - Format
#                - pretty : Do not show the date and priority
#
write_log() {

  # Check log severity
  case "$3" in
    "debug")
      severity="DEBUG"
      ;;
    "info")
      severity="INFO"
      ;;
    "notice")
      severity="WARNING"
      ;;
    "err")
      severity="ERROR"
      ;;
    "crit")
      severity="CRITICAL ERROR"
      ;;
    "alert")
      severity="ALERT"
      ;;
    "emerg")
      severity="EMERGENCY"
      ;;
    "*")
      write_log $1 "err" "Internal error: unrecognized priority: $3" $4
      exit 1
      ;;
  esac

  # Log to syslog
  if [[ "$5" =~ ^(logonly|all)$ ]]; then
      if [[ "${SYSLOG_UDP_ENABLED}" == "true" ]]; then
          # Send log to remote syslog server using logger
          logger -n "${LOG_IP}" -P "${LOG_PORT}" -t "${tag}" "${4}"
      else
          # Log locally
          logger -t "${tag}" "${4}"
      fi
  fi

  # Log to Stdout
  if [[ "${5}" =~ ^(outonly|all)$ ]]; then
      if [[ "${6}" == "pretty" ]]; then
          echo "${4}" >&2
      else
          echo "[$(date +'%Y-%m-%d %H:%M:%S')]: $@" >&2
      fi
  fi

}



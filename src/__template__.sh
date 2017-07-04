#!/usr/bin/env bash

############################################################
# Run with --help for description.
#
# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
############################################################

__author__="${FULL_NAME}"
__copyright__="Copyright (c) 2017 OSIsoft, LLC"
__license__="Apache 2.0"
__version__="${VERSION}"

############################################################
# Change the current directory to the directory where this
# script is located
############################################################
SCRIPT=$_
if [[ "$SCRIPT" != "$0" ]]
then
  # See https://unix.stackexchange.com/questions/4650/determining-path-to-sourced-shell-script
  SOURCING=1
  SCRIPT=${BASH_SOURCE[@]}
  if [ "$SCRIPT" == "" ]
  then
    SCRIPT=$_
  fi
else
  SOURCING=0
  SCRIPT=$0
fi

pushd `dirname "$SCRIPT"` > /dev/null

SCRIPTNAME=$(basename "$SCRIPT")

############################################################
# Usage text for this script
############################################################
USAGE="$SCRIPTNAME

Description

Commands:
  -a, --activate  Activate virtual envirnoment
  -l, --lint      Check source code with lint
  Anything else   Show this help text

Multiple commands can be specified but they all must all be
specified separately (-al is not supported).

Exit status code:
  This script exits with status code 1 when errors occur (e.g., 
  tests fail) except when it is 'sourced.'"

############################################################
# Execute the command specified in $OPTION
############################################################
execute_command() {
  if [ "$OPTION" == "ACTIVATE" ]
  then
    echo "Activating..."

    # Example: check last shell command for failure
    if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
    then
      exit 1
    fi

  elif [ "$OPTION" == "LINT" ]
  then
    echo "Linting..."

  fi
}

############################################################
# Process arguments
############################################################
RETURN=0

if [ $# -gt 0 ]
then
  for i in "$@"
  do
    case $i in
      -a|--activate)
        OPTION="ACTIVATE"
        ;;

      -l|--lint)
        OPTION="LINT"
        ;;

      *)
        echo "${USAGE}" # anything including -h :]
        RETURN=1
        break
        ;;
    esac

    execute_command
  done
else
  echo "${USAGE}"
  RETURN=1
fi

############################################################
# Unset all temporary variables created by this script
# and revert to the previous current directory
# when this script has been sourced
############################################################
if [ $SOURCING -gt 0 ]
then
  popd > /dev/null

  unset OPTION
  unset RETURN
  unset SCRIPT
  unset SCRIPTNAME
  unset SOURCING
  unset USAGE
else
  exit $RETURN
fi


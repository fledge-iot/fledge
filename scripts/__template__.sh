#!/usr/bin/env bash

############################################################
# Run with --help for description.
#
# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END
############################################################

__author__="${FULL_NAME}"
__copyright__="Copyright (c) 2017 OSIsoft, LLC"
__license__="Apache 2.0"
__version__="${VERSION}"

############################################################
# Sourcing?
############################################################
if [[ "$0" != "$BASH_SOURCE" ]]
then
  # See https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced/23009039#23009039
  # This only works reliably with 'bash'. Other shells probably
  # can not 'source' this script.
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

############################################################
# Change the current directory to the directory where this
# script is located
############################################################
pushd `dirname "$SCRIPT"` > /dev/null

SCRIPTNAME=$(basename "$SCRIPT")
SCRIPT_AND_VERSION="$SCRIPTNAME $__version__"

############################################################
# Usage text for this script
############################################################
USAGE="$SCRIPT_AND_VERSION

DESCRIPTION
  This is a script template.

OPTIONS
  Multiple commands can be specified but they all must be
  specified separately (-hv is not supported).

  -h, --help      Display this help text
  -v, --version   Display this script's version information

EXIT STATUS
  This script exits with status code 1 when errors occur (e.g., 
  tests fail) except when it is sourced.
  
EXAMPLES
  1) $SCRIPTNAME --version"

############################################################
# Execute the command specified in $OPTION
############################################################
execute_command() {
  if [ "$OPTION" == "HELP" ]
  then
    echo "${USAGE}"

  elif [ "$OPTION" == "VERSION" ]
  then
    echo $SCRIPT_AND_VERSION

    # Example: check last shell command for failure
    if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
    then
      exit 1
    fi

  fi
}

############################################################
# Process arguments
############################################################
if [ $# -gt 0 ]
then
  for i in "$@"
  do
    case $i in
      -h|--help)
        OPTION="HELP"
      ;;

      -v|--version)
        OPTION="VERSION"
      ;;

      *)
        echo "Unrecognized option: $i"

        if [ $SOURCING -lt 1 ]
        then
          exit 1
        fi

        break
      ;;
    esac

    execute_command
  done
else
  echo "${USAGE}"

  if [ $SOURCING -lt 1 ]
  then
    exit 1
  fi
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
  unset SCRIPT
  unset SCRIPTNAME
  unset SCRIPT_AND_VERSION
  unset SOURCING
  unset USAGE
fi


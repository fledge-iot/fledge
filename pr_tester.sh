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
  This script triggers when any of pull request is open and on subsequent commits in github and generate report results.
  And detailed result display as in below Jobs:
  i) foglamp_lint_check_tester -> only responsible for lint check
  ii) foglamp_unit_and_integration_tester => only responsible to run ALL Python tests

  More documentation available on g-drive. See https://scaledb.atlassian.net/browse/FOGL-570

OPTIONS
  Multiple commands can be specified but they all must be
  specified separately (-hv is not supported).

  -h, --help      Display this help text
  -v, --version   Display this script's version information
  -l, --lint      Run pylint. Writes output to
                  pylint_report.log
  -p, --py-test   Run ALL Python tests

EXIT STATUS
  This script exits with status code 1 when errors occur (e.g.,
  tests fail) except when it is sourced.

EXAMPLES
  1) $SCRIPTNAME -l
  2) $SCRIPTNAME -p"

############################################################
# Execute the command specified in $OPTION
############################################################
execute_command() {
  # These commands don't need a virtual environment
  if [ "$OPTION" == "HELP" ]
  then
    echo "${USAGE}"
    return

  elif [ "$OPTION" == "VERSION" ]
  then
    echo $SCRIPT_AND_VERSION
    return
  fi

  if [ "$OPTION" == "LINT" ]
  then
    # Get files name list
    FILE_NAMES_LIST=$(git diff-tree --no-commit-id --name-only -r ${ghprbActualCommit})

    # find py files only
    PY_FILES_ONLY=$(find $FILE_NAMES_LIST -name "*.py")
    PY_FILE_EXISTS=$(echo -n $PY_FILES_ONLY | wc -m)

    if [ $PY_FILE_EXISTS -gt 0 ]
        then
        # Change directory only to run only build.sh commands
        cd src/python

        # clean virtual environment and pylint_report log file
        rm -rf venv
        rm -rf pylint_report*.log
        source build.sh -c

        # activate virtual env
        source build.sh -a

        # install develop dependencies
        make develop

        # pylint check and remove src/python from path
        FILE_WITHOUT_ABSOLUTE_PATH="$(echo $PY_FILES_ONLY | sed 's/src\/python\///g')"
        pylint ${FILE_WITHOUT_ABSOLUTE_PATH} > pylint_report.log

        # lint check result on the basis of code rate and exit code accordingly
        RESULT=$(grep -i "Your code has been rated at 10.00/10" pylint_report.log)
        FILE_CONTENT_LENGTH=$(echo -n ${RESULT} | wc -m)
        if [ $FILE_CONTENT_LENGTH -gt 0 ]
            then
                exit 0 # PASS
        else
           exit 1 # FAIL
        fi
    fi
  fi

  if [ "$OPTION" == "TEST_PYTHON" ]
  then
    # Change directory only to run build.sh commands
    cd src/python

    # clean environment
    rm -rf venv
    source build.sh -c

    # activate virtual env
    source build.sh -a

    # install develop dependencies
    make develop

    # pytest result handle on the basis of errors/failures and exit code accordingly
    RESULT=$(pytest tests/ --alluredir=../../allure/unit_test_report | grep -i 'ERRORS\|FAILURE')
    OUTPUT=$(echo -n ${RESULT} | wc -m)

    if [ $OUTPUT -gt 0 ]
        then
          exit 1 # FAIL
    else
        exit 0 # PASS
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

      -l|--lint)
        OPTION="LINT"
      ;;

      -p|--py-test)
        OPTION="TEST_PYTHON"
      ;;

      *)
        echo "Unrecognized option: $i"

        break
      ;;
    esac

    execute_command
  done
else
  echo "${USAGE}"
fi

############################################################
# Unset all temporary variables created by this script
# and revert to the previous current directory
# when this script has been sourced
############################################################
if [ $SOURCING -gt 0 ]
then
  popd > /dev/null

  if [ "$OPTION" == "LINT" ]
    then
     unset FILE_NAMES_LIST
     unset PY_FILES_ONLY
     unset PY_FILE_EXISTS
     unset FILE_WITHOUT_ABSOLUTE_PATH
     unset RESULT
     unset FILE_CONTENT_LENGTH
  fi

  if [ "$OPTION" == "TEST_PYTHON" ]
    then
     unset RESULT
     unset OUTPUT
  fi

  unset OPTION
  unset SCRIPT
  unset SCRIPTNAME
  unset SCRIPT_AND_VERSION
  unset SOURCING
  unset USAGE
fi
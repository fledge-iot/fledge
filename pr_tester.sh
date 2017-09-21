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
  Tools for Jenkins.

OPTIONS
  Multiple commands can be specified but they all must be
  specified separately (-hv is not supported).

  -h, --help      Display this help text
  -v, --version   Display this script's version information
  -l, --lint      Run pylint. Writes output to
                  pylint-report.txt
  -p, --py-test   Run only Python tests

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
    LINT_CHECK_FILES=$(find $FILE_NAMES_LIST -name "*.py")
    LINT_CHECK_FILENAME_LENGTH=$(echo -n $LINT_CHECK_FILES | wc -m)

    if [ $LINT_CHECK_FILENAME_LENGTH -gt 0 ]
        then
        # Change directory only to run only build.sh commands
        cd src/python

        # clean virtual environment and pylint-report log file
        rm -rf venv
        rm -rf pylint_report*.log
        source build.sh -c

        # activate virtual env
        source build.sh -a

        # install develop dependencies
        make develop

        # pylint check and remove src/python from path
        OUTPUT="$(echo $LINT_CHECK_FILES | sed 's/src\/python\///g')"
        pylint ${OUTPUT} > pylint_report.log

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
    RESULT=$(pytest tests/test.py --alluredir=../../allure/unit_test_report | grep -i 'ERRORS\|FAILURE')
    OUTPUT=$(echo -n ${RESULT} | wc -m)

    if [ $OUTPUT -gt 0 ]
        then
          exit 1 #FAIL
    else
        exit 0 #"PASS
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
     unset LINT_CHECK_FILES
     unset LINT_CHECK_FILENAME_LENGTH
     unset OUTPUT
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
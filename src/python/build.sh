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
# Change the cwd to the directory where this script
# is located
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

pushd `dirname "$SCRIPT"` > /dev/null
SCRIPTNAME=$(basename "$SCRIPT")
SCRIPT_AND_VERSION="$SCRIPTNAME $__version__"

############################################################
# Usage text for this script
############################################################
USAGE="$SCRIPT_AND_VERSION

DESCRIPTION
  Tools for FogLAMP

SOURCING THIS SCRIPT
  $ source build.sh [options]
  or:
  $ . build.sh [options]

  Sourcing is only guaranteed to work reliably from bash.

  Sourcing this script leaves the virtual environment active
  so, for example, the 'python' command actually runs python3.
  Deactivate the virtual environment via the 'deactivate' shell
  command. The environment variable VENV_PATH contains a path
  to the virtual environment's directory.

OPTIONS
  Multiple commands can be specified but they all must be
  specified separately (-hv is not supported).

  -a, --activate    Create and activate the Python virtual
                    environment and exit. Do not install
                    dependencies. Must invoke via 'source.'
  -c, --clean       Delete the virtual environment and remove
                    build and cache directories
  -d, --doc         Generate HTML in docs/_build
  --doc-build-test  Run docs/check_sphinx.py
  --deactivate      Deactivate the virtual environment. Must
                    invoke via 'source.'
  -h, --help        Display this help text
  -i, --install     Install production Python dependencies
                    and FogLAMP-specific packages and scripts
  --install-dev-dep Install Python dependencies for 
                    development and testing
  -l, --lint        Run pylint. Writes output to 
                    pylint-report.txt
  --live-doc        Run a local webserver that serves files in 
                    docs/_build and monitors modifications to
                    files in docs/ and regenerates HTML
  -p, --py-test     Run only Python tests
  -r, --run         Start FogLAMP
  -s, --service     Start the FogLAMP service
  -t, --test        Run all tests
  -u, --uninstall   Remove FogLAMP packages and scripts
  -v, --version     Display this script's version information

EXIT STATUS
  This script exits with status code 1 when errors occur (e.g., 
  tests fail) except when it is sourced.

EXAMPLES
  1) source $SCRIPTNAME -a"

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

  # The following commands need a virtual environment
  IN_VENV=$(python3 -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')
  if [ $? -gt 0 ]
  then
    echo "*** python3 not found"
    if [ $SOURCING -lt 1 ]
    then
      exit 1
    fi
    return
  fi

  if [ $IN_VENV -gt 0 ]
  then
    echo "-- A virtual environment is already active"
  fi 

  if [ "$OPTION" == "ACTIVATE" ]
  then
    if [ $IN_VENV -gt 0 ]
    then
      return
    fi

    if [ $SOURCING -lt 1 ]
    then
      echo "*** Source this script when using --activate"
      exit 1
    fi
  fi

  if [ "$OPTION" == "DEACTIVATE" ]
  then
    if [ $IN_VENV -gt 0 ] 
    then
      # Deactivate doesn't work unless sourcing
      if [ $SOURCING -lt 1 ]
      then
        echo "*** Source this script when using --deactivate"
        exit 1
      fi

      echo "-- Deactivating virtual environment"
      deactivate
    fi
    return
  fi

  VENV_PATH="`pwd`/venv/$HOSTNAME"

  if [ "$OPTION" == "CLEAN" ]
  then
    if [ $IN_VENV -gt 0 ] 
    then
      # Deactivate doesn't work unless sourcing
      if [ $SOURCING -lt 1 ]
      then
        echo "*** Source this script when using --clean when virtual environment is active"
        exit 1
      fi

      echo "-- Deactivating virtual environment"
      deactivate
    fi

    echo "-- Removing $VENV_PATH"
    rm -rf "$VENV_PATH"

    make clean
    return
  fi

  if [ $IN_VENV -lt 1 ]
  then
    if [ ! -f "$VENV_PATH/bin/activate" ]
    then
      echo "-- Installing virtualenv"
      pip3 install virtualenv 2> /dev/null

      if [ $? -gt 0 ]
      then
        pip install virtualenv
      fi

      if [ $? -gt 0 ]
      then
        echo "*** pip failed installing virtualenv"
        if [ $SOURCING -lt 1 ]
        then
          exit 1
        fi
        return
      fi

      # Find Python3.5 or Python3 if it doesn't exist
      python_path=$( which python3.5 )

      if [ $? -gt 0 ]
      then
        echo "*** python3.5 not found"
        python_path=$( which python3 )

        if [ $? -gt 0 ]
        then
          echo "*** python3 not found"
          if [ $SOURCING -lt 1 ]
          then
            exit 1
          fi
          return
        fi
      fi

      echo "-- Creating virtual environment for ${python_path}"
      virtualenv "--python=$python_path" "$VENV_PATH"
    fi

    echo "-- Activating the virtual environment at $VENV_PATH"
    source "$VENV_PATH/bin/activate"

    IN_VENV=$(python3 -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')

    if [ $? -gt 0 ] || [ $IN_VENV -lt 1 ]
    then
      echo "*** Activating virtual environment failed"
      return
    fi
  fi

  if [ "$OPTION" == "ACTIVATE" ]
  then
    return
  fi
  
  # TODO this will be deleted
  make create-env

  if [ "$OPTION" == "DEV_DEP" ]
  then
    make install-dev-dep

  elif [ "$OPTION" == "LINT" ]
  then
    make lint
    if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
    then
      exit 1
    fi

  elif [ "$OPTION" == "TEST" ]
  then
    make test
    if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
    then
      exit 1
    fi

  elif [ "$OPTION" == "TEST_PYTHON" ]
  then
    make py-test
    if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
    then
      exit 1
    fi

  elif [ "$OPTION" == "INSTALL" ]
  then
    make install
    if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
    then
      exit 1
    fi

  elif [ "$OPTION" == "RUN" ]
  then
    make install
    if [ $? -gt 0 ] 
    then
      if [ $SOURCING -lt 1 ]
      then
        exit 1
      else
        return
      fi
    fi
    foglamp

  elif [ "$OPTION" == "RUN_DAEMON" ]
  then
    make install
    if [ $? -gt 0 ] 
    then
      if [ $SOURCING -lt 1 ]
      then
        exit 1
      else
        return
      fi
    fi
    foglampd

  elif [ "$OPTION" == "BUILD_DOC" ]
  then
    make doc
    if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
    then
      exit 1
    fi

  elif [ "$OPTION" == "TEST_DOC_BUILD" ]
  then
    make doc-build-test
    if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
    then
      exit 1
    fi
    
  elif [ "$OPTION" == "LIVE_DOC" ]
  then
    make live-doc
    if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
    then
      exit 1
    fi

  elif [ "$OPTION" == "UNINSTALL" ]
  then
    pip uninstall FogLAMP <<< y
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
      -a|--activate)
        OPTION="ACTIVATE"
      ;;

      -c|--clean)
        OPTION="CLEAN"
      ;;

      --deactivate)
        OPTION="DEACTIVATE"
      ;;

      -d|--doc)
        OPTION="BUILD_DOC"
      ;;

      --doc-build-test)
        OPTION="TEST_DOC_BUILD"
      ;;

      -h|--help)
        OPTION="HELP"
      ;;

      -i|--install)
        OPTION="INSTALL"
      ;;

      --install-dev-dep)
        OPTION="DEV_DEP"
      ;;

      -l|--lint)
        OPTION="LINT"
      ;;

      --live-doc)
        OPTION="LIVE_DOC"
      ;;

      -p|--py-test)
        OPTION="TEST_PYTHON"
      ;;

      -r|--run)
        OPTION="RUN"
      ;;

      -s|--service)
        OPTION="RUN_DAEMON"
      ;;

      -t|--test)
        OPTION="TEST"
      ;;
      
      -u|--uninstall)
        OPTION="UNINSTALL"
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
# when this script has been sourced. Leave VENV_PATH.
############################################################
if [ $SOURCING -gt 0 ]
then
  popd > /dev/null

  unset IN_VENV
  unset OPTION
  unset SCRIPT
  unset SCRIPTNAME
  unset SOURCING
  unset USAGE
fi


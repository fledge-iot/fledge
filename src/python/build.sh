#!/bin/bash

# FOGLAMP_PRELUDE_BEGIN
# {{FOGLAMP_LICENSE_DESCRIPTION}}
# See: http://foglamp.readthedocs.io/
#
# Copyright (c) 2017 OSIsoft, LLC
# License: Apache 2.0
# FOGLAMP_PRELUDE_END
#
# __author__ = ${FULL_NAME}
# __version__ = ${VERSION}
#
# Run with --help for description.

# Change the cwd to the directory where this script
# is located
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

USAGE="=== $SCRIPTNAME ===
Build utilities for FogLAMP.

Sourcing this script:
  $ source build.sh [options]
  or:
  $ . build.sh [options]

  Sourcing this script activates a virtual environment so, for
  example, the 'python' command actually python3. Deactivate 
  the virtual environment by running \"deactivate\". The 
  environment variable VENV_PATH contains a path to the virtual
  environment's directory.

Options:
  -a, --activate    Create and activate the Python virtual
                    environment and exit. Do not install
                    dependencies. Must invoke via 'source.'
   -c, --clean      Delete the virtual environment and remove
                    build and cache directories
  -d, --doc         Generate HTML in doc/_build directory
  --doc-build-test  Run docs/check_sphinx.py
  --deactivate      Deactivate the virtual environment. Must
                    invoke via 'source.'
  -i, --install     Install production Python dependencies
                    and FogLAMP-specific packages and scripts
  --install-all-dep Install all Python dependencies
  --install-dev-dep Install Python dependencies for 
                    production and testing
  -l, --lint        Run pylint. Writes output to 
                    pylint-report.txt
  --live-doc        Run a local webserver that serves files in 
                    doc/_build and monitors modifications to
                    files in doc/ and regenerates HTML
  -p, --py-test     Run only Python tests
  -r, --run         Start FogLAMP
  -s, --service     Start FogLAMP service
  -t, --test        Run all tests
  -u, --uninstall   Remove FogLAMP packages and scripts
  Anything else     Show this help text

Exit status code:
  When this script is not invoked via 'source', it exits
  with status code 1 when errors occur (e.g., tests fail)"

setup_and_run() {
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
            # deactivate doesn't work unless sourcing
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
            # deactivate doesn't work unless sourcing
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
                pip install -r requirements-virtualenv.txt
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

        IN_VENV=$(python -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')

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

    if [ "$OPTION" == "ALLDEP" ]
    then
        make install-all-requirements

    elif [ "$OPTION" == "DEVDEP" ]
    then
        make install-dev-requirements

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

OPTION=''

if [ $# -gt 0 ]
  then
     for i in "$@"
     do
         case $i in

           -a|--activate)
             OPTION="ACTIVATE"
             ;;

           --install-all-dep)
             OPTION="ALLDEP"
             ;;

           --install-dev-dep)
             OPTION="DEVDEP"
             ;;

           --deactivate)
             OPTION="DEACTIVATE"
             ;;

           -l|--lint)
             OPTION="LINT"
             ;;

           -t|--test)
             OPTION="TEST"
             ;;

           -p|--py-test)
             OPTION="TEST_PYTHON"
             ;;

           -i|--install)
             OPTION="INSTALL"
             ;;

            -r|--run)
             OPTION="RUN"
             ;;

            -s|--service)
             OPTION="RUN_DAEMON"
             ;;

            -u|--uninstall)
             OPTION="UNINSTALL"
             ;;

            -c|--clean)
             OPTION="CLEAN"
             ;;

            -d|--doc)
             OPTION="BUILD_DOC"
             ;;

            --doc-build-test)
              OPTION="TEST_DOC_BUILD"
              ;;

            --live-doc)
              OPTION="LIVE_DOC"
              ;;

            *)
             echo "${USAGE}" # anything including -h :]
             break
             ;;
         esac
         setup_and_run
     done
  else
     setup_and_run
fi

popd > /dev/null

# Unset all temporary variables used above
if [ $SOURCING -gt 0 ]
then
    unset IN_VENV
    unset OPTION
    unset SCRIPT
    unset SCRIPTNAME
    unset SOURCING
    unset USAGE
fi


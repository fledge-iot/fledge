#!/bin/bash

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

Activates a Python virtual environment for python3.5 or 
python3 if python3.5 can not be found. Installs 
Python dependencies (per requirements.txt) unless 
--activate is provided. Additional capabilities are 
available - see the options below.

Sourcing this script:
  source build.sh [options]
  or:
  . build.sh [options]

  Sourcing this script causes the shell to inherit the virtual
  environment so, for example, the 'python' command actually 
  runs python3. Deactivate the virtual environment by running
  \"deactivate\". The environment variable VENV_PATH is
  created.

Options:
  -a, --activate   Create and activate the virtual environment
                   and exit. Do not install dependencies. Must
                   must invoke via 'source.'
  -c, --clean      Delete the virtual environment and remove
                   build and cache directories
  -d, --doc        Generate HTML in doc/_build directory
  --doc-build-test Run docs/check_sphinx.py
  --deactivate     Deactivate the virtual environment. Must
                   invoke via 'source.'
  -i, --install    Install FogLAMP packages and scripts
  -l, --lint       Run pylint. Writes output to 
                   pylint-report.txt
  --live-doc       Run a local webserver that serves files in 
                   doc/_build and monitors modifications to
                   files in doc/ and regenerates HTML
  -p, --py-test    Run only Python tests
  -r, --run        Start FogLAMP
  -s, --service    Start FogLAMP service
  -t, --test       Run all tests
  -u, --uninstall  Remove FogLAMP packages and scripts
  Anything else    Show this help text

Exit status code:
  When this script is not invoked via 'source', it exits
  with status code 1 when errors occur (e.g., tests fail)"

setup_and_run() {
    IN_VENV=$(python -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')

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

            echo "-- Deactivating virtualenv"
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

            echo "-- Deactivating virtualenv"
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

            echo "-- Creating virtualenv for ${python_path}"
            virtualenv "--python=$python_path" "$VENV_PATH"
        fi

        echo "-- Activating the virtualenv at $VENV_PATH"
        source "$VENV_PATH/bin/activate"

        IN_VENV=$(python -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')

        if [ $IN_VENV -lt 1 ]
        then
            echo "*** virtualenv failed"
            return
        fi
    fi

    if [ "$OPTION" == "ACTIVATE" ]
    then
        return
    fi
    
    make install-py-requirements
    make create-env

    if [ "$OPTION" == "LINT" ]
    then
        echo "Running lint checker"
        make lint
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$OPTION" == "TEST" ]
    then
        echo "Running all tests"
        make test
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$OPTION" == "TEST_PYTHON" ]
    then
        echo "Running pytest"
        make py-test
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$OPTION" == "INSTALL" ]
    then
        pip install -e .
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$OPTION" == "RUN" ]
    then
        pip install -e .
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi
        foglamp

    elif [ "$OPTION" == "RUN_DAEMON" ]
    then
        pip install -e .
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi
        foglampd

    elif [ "$OPTION" == "BUILD_DOC" ]
    then
        echo "Building doc"
        make doc
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$OPTION" == "TEST_DOC_BUILD" ]
    then
        echo "Running Sphinx docs build test"
        make doc-build-test
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi
        
    elif [ "$OPTION" == "LIVE_DOC" ]
    then
        echo "Observe the changes in doc and update HTML live"
        make live-doc
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$OPTION" == "UNINSTALL" ]
    then
        echo "This will remove the package"
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


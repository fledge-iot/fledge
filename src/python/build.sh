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

usage="=== $SCRIPTNAME ===

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
  \"deactivate\". 

Options:
  -a, --activate  Create and activate the virtual environment
                  and exit. Do not install dependencies.
                  (must invoke via 'source')
  -c, --clean     Delete the virtual environment and remove
                  'build' directories
  -d, --doc       Generate html in doc/_build directory
  --doc-build-test Run docs/check_sphinx.py
  --deactivate    Deactivate the virtual environment
                  (must invoke via 'source')
  -i, --install   Install FogLAMP packages and scripts
  -l, --lint      Run pylint. Writes output to 
                  pylint-report.txt
  --live-doc      Live doc serves the built html for docs/ on localhost, observe the changes in doc and update the html live
  -p, --py-test    Run only Python tests
  -r, --run       Start FogLAMP
  -s, --service   Start FogLAMP daemon
  -t, --test      Run all tests
  -u, --uninstall Remove FogLAMP packages and scripts
  Anything else   Show this help text

Exit status code:
  When this script is not invoked via 'source', it exits
  with status code 1 when errors occur (e.g., tests fail)"

setup_and_run() {
    ALREADY_IN_VENV=$(python -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')

    if [ $ALREADY_IN_VENV -gt 0 ]
    then
        echo "-- A virtual environment is already active"
    fi

    if [ "$option" == "ACTIVATE" ]
    then
        if [ $ALREADY_IN_VENV -gt 0 ]
        then
            return
        fi

        if [ $SOURCING -lt 1 ]
        then
            echo "*** Source this script when using --activate"
            exit 1
        fi
    fi

    if [ "$option" == "DEACTIVATE" ]
    then
        if [ $ALREADY_IN_VENV -gt 0 ]
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

    VENV_PATH="venv/$HOSTNAME"

    if [ "$option" == "CLEAN" ]
    then
        if [ $ALREADY_IN_VENV -gt 0 ]
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

        echo "-- Removing `pwd`/$VENV_PATH"
        rm -rf "$VENV_PATH"

        make clean
        return
    fi

    if [ $ALREADY_IN_VENV -lt 1 ]
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
            #

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

        echo "-- Activating the virtualenv at `pwd`/$VENV_PATH"
        source "$VENV_PATH/bin/activate"

        IN_VENV=$(python -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')

        if [ $IN_VENV -lt 1 ]
        then
            echo "*** virtualenv failed"
            return
        fi
    fi

    if [ "$option" == "ACTIVATE" ]
    then
        return
    fi

    make install-py-requirements
    make create-env

    if [ "$option" == "LINT" ]
    then
        echo "Running lint checker"
        make lint
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$option" == "TEST" ]
    then
        echo "Running all tests"
        make test
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$option" == "TEST_PYTHON" ]
    then
        echo "Running pytest"
        make py-test
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$option" == "INSTALL" ]
    then
        pip install -e .

    elif [ "$option" == "RUN" ]
    then
        foglamp

    elif [ "$option" == "RUN_DAEMON" ]
    then
        foglamp-d

    elif [ "$option" == "BUILD_DOC" ]
    then
        echo "Building doc"
        make doc
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$option" == "TEST_DOC_BUILD" ]
    then
        echo "Running Sphinx doc build test"
        make doc-build-test
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$option" == "LIVE_DOC" ]
    then
        echo "Observe the changes in doc and update the html live"
        make live-doc
        if [ $? -gt 0 ] && [ $SOURCING -lt 1 ]
        then
            exit 1
        fi

    elif [ "$option" == "UNINSTALL" ]
    then
        echo "This will remove the package"
        pip uninstall FogLAMP <<< y
    fi
}

option=''

if [ $# -gt 0 ]
  then
     for i in "$@"
     do
         case $i in

           -a|--activate)
             option="ACTIVATE"
             ;;

           --deactivate)
             option="DEACTIVATE"
             ;;

           -l|--lint)
             option="LINT"
             ;;

           -t|--test)
             option="TEST"
             ;;

           -p|--py-test)
             option="TEST_PYTHON"
             ;;

           -i|--install)
             option="INSTALL"
             ;;

            -r|--run)
             option="RUN"
             ;;

            -s|--service)
             option="RUN_DAEMON"
             ;;

            -u|--uninstall)
             option="UNINSTALL"
             ;;

            -c|--clean)
             option="CLEAN"
             ;;

            -d|--doc)
             option="BUILD_DOC"
             ;;

            --doc-build-test)
              option="TEST_DOC_BUILD"
              ;;

            --live-doc)
              option="LIVE_DOC"
              ;;

            *)
             echo "${usage}" # anything including -h :]
             break
             ;;
         esac
         setup_and_run
     done
  else
     setup_and_run
fi

popd > /dev/null

#!/usr/bin/env bash

# Default values
export FLEDGE_DATA=./plugin_cfg/sqlite          # Select the persistent storage plugin
export storage_exec=$FLEDGE_ROOT/services/fledge.services.storage
export TZ='Etc/UTC'

show_configuration () {

	echo "Fledge unit tests for the SQLite plugin"

	echo "Starting storage layer      :$storage_exec:"
	echo "timezone                    :$TZ:"
	echo "expected dir                :$expected_dir:"
	echo "configuration               :$FLEDGE_DATA:"
	echo "database file fledge        :$DEFAULT_SQLITE_DB_FILE:"
	echo "database file readings      :$DEFAULT_SQLITE_DB_READINGS_FILE:"
}


#
# evaluates : FLEDGE_DATA, storage_exec, TZ, and expected_dir
#
if [[ "$@" != "" ]];
then
	# Handles input parameters
	SCRIPT_NAME=`basename $0`
	options=`getopt -o c:s:t: --long configuration:,storage_exec:,timezone: -n "$SCRIPT_NAME" -- "$@"`
	eval set -- "$options"

	while true ; do
	    case "$1" in
	        -c|--configuration)
	            export FLEDGE_DATA="$2"
	            shift 2
	            ;;

	        -s|--storage_exec)
	            export storage_exec="$2"
	            shift 2
	            ;;

	        -t|--timezone)
				export TZ="$2"
	            shift 2
	            ;;
	        --)
	            shift
	            break
	            ;;
	    esac
	done
fi

# Converts '/' to '_' and to upper case
step1="${TZ/\//_}"
expected_dir="expected_${step1^^}"

if [[ "$storage_exec" != "" ]] ; then

	show_configuration
	$storage_exec
	sleep 1

elif [[ "${FLEDGE_ROOT}" != "" ]] ; then

	show_configuration
	$storage_exec
	sleep 1

else
	echo Must either set FLEDGE_ROOT or provide storage service to test
	exit 1
fi

#
# Main
#
export IFS=","
testNum=1
n_failed=0
n_passed=0
n_unchecked=0

./testSetup.sh > /dev/null 2>&1
sleep 5

rm -f failed
rm -rf results
mkdir results
cat testset | while read name method url payload optional; do
#sleep 0.003
echo -n "Test $testNum ${name}: "
if [ "$payload" = "" ] ; then
	output=$(curl -X $method $url -o results/$testNum 2>/dev/null)
	curlstate=$?
else
	output=$(curl -X $method $url -d@payloads/$payload -o results/$testNum 2>/dev/null)
	curlstate=$?
fi

# Forces the creation on an empty file if the output of the curl command is empty
# it is needed for the behavior of the curl command in RHEL/CentOS
if [ "$output" = "" ] ; then

	touch results/$testNum
else
	echo -n "${output}" > results/$testNum
fi

if [ "$optional" = "" ] ; then
	if [ ! -f ${expected_dir}/$testNum ]; then
		n_unchecked=`expr $n_unchecked + 1`
		echo Missing expected results in :${expected_dir}: for test $testNum - result unchecked
	else
		cmp -s results/$testNum ${expected_dir}/$testNum
		if [ $? -ne "0" ]; then
			echo Failed
			n_failed=`expr $n_failed + 1`
			if [ "$payload" = "" ]
			then
				echo Test $testNum  ${name} curl -X $method $url >> failed
			else
				echo Test $testNum  ${name} curl -X $method $url -d@payloads/$payload  >> failed
			fi
			(
			unset IFS
			echo "   " Expected: "`cat ${expected_dir}/$testNum`" >> failed
			echo "   " Got:     "`cat results/$testNum`" >> failed
			)
			echo >> failed
		else
			echo Passed
			n_passed=`expr $n_passed + 1`
		fi
	fi
elif [ "$optional" = "checkstate" ] ; then
	if [ $curlstate -eq 0 ] ; then
		echo Passed
		n_passed=`expr $n_passed + 1`
	else
		echo Failed
		n_failed=`expr $n_failed + 1`
		if [ "$payload" = "" ]
		then
			echo Test $testNum  curl -X $method $url >> failed
		else
			echo Test $testNum  curl -X $method $url -d@payloads/$payload  >> failed
		fi
	fi
fi
#sleep 2
testNum=`expr $testNum + 1`
rm -f tests.result
echo $n_failed Tests Failed 		>  tests.result
echo $n_passed Tests Passed 		>> tests.result
echo $n_unchecked Tests Unchecked	>> tests.result
done
./testCleanup.sh > /dev/null
cat tests.result
rm -f tests.result
if [ -f "failed" ]; then
	echo
	echo "Failed Tests"
	echo "============"
	cat failed
	exit 1
fi
exit 0

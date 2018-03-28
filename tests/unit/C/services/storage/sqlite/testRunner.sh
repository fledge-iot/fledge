#!/bin/sh
export FOGLAMP_DATA=.
if [ $# -eq 1 ] ; then
	echo Starting storage layer $1
	$1 
elif [ "${FOGLAMP_ROOT}" != "" ] ; then
	echo Starting storage service in $FOGLAMP_ROOT
	$FOGLAMP_ROOT/services/storage
	sleep 1
else
	echo Must either set FOGLAMP_ROOT or provide storage service to test
	exit 1
fi

export IFS=","
testNum=1
n_failed=0
n_passed=0
n_unchecked=0
./testSetup.sh > /dev/null 2>&1
rm -f failed
rm -rf results
mkdir results
cat testset | while read name method url payload optional; do
#sleep 0.003
echo -n "Test $testNum ${name}: "
if [ "$payload" = "" ] ; then
	curl -X $method $url -o results/$testNum >/dev/null 2>&1
	curlstate=$?
else
	curl -X $method $url -d@payloads/$payload -o results/$testNum >/dev/null 2>&1
	curlstate=$?
fi
if [ "$optional" = "" ] ; then
	if [ ! -f expected/$testNum ]; then
		n_unchecked=`expr $n_unchecked + 1`
		echo Missing expected results for test $testNum - result unchecked
	else
		cmp -s results/$testNum expected/$testNum
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
			echo "   " Expected: "`cat expected/$testNum`" >> failed
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
#./testCleanup.sh > /dev/null
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

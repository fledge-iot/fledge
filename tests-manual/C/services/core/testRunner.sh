#!/bin/sh

set -e

if [ "${FOGLAMP_ROOT}" = "" ] ; then
        echo "Must set FOGLAMP_ROOT variable"
        exit 1
fi

testNum=1
n_failed=0
n_passed=0
n_unchecked=0

export foglamp_core_port=9393

# Start FoglampCore an storage service
./testSetup.sh

rm -f failed
rm -rf results
mkdir results

cat testset | while read name method url payload optional; do
	# Add FogLAMP core port
	url=`echo ${url} | sed -e "s/_CORE_PORT_/${foglamp_core_port}/"`

	echo -n "Test [$testNum] ${name}: "
	#echo "Test [$testNum] ${name}: "
	#echo "${method} ${url}"
	if [ "$payload" = "" ] ; then
		echo "curl -X $method $url -o results/$testNum"
		curl -X $method $url -o results/$testNum >/dev/null 2>&1
		curlstate=$?
	else
		curl -X $method $url -d@payloads/$payload -o results/$testNum >/dev/null 2>&1
		curlstate=$?
	fi
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
			echo "   " Expected: "`cat expected/$testNum`" >> failed
			echo "   " Got:     "`cat results/$testNum`" >> failed
			)
			echo >> failed
		else
			echo Passed
			n_passed=`expr $n_passed + 1`
		fi
	fi

	testNum=`expr $testNum + 1`
	rm -f tests.result
	echo $n_failed Tests Failed             >  tests.result
	echo $n_passed Tests Passed             >> tests.result
	echo $n_unchecked Tests Unchecked       >> tests.result
done

cat tests.result
rm -f tests.result

if [ -f "failed" ]; then
        echo
        echo "Failed Tests"
        echo "============"
        cat failed
        exit 1
fi

####
# Add as last test shutdown of core and storage.
# Core shutdown not implemented yet
# Storage can be done thss way
#
#  storageServiceURL="http://127.0.0.1:${foglamp_core_port}/foglamp/service?name=FogLAMP%20Storage"
#  storageInfo=`curl -s ${storageServiceURL}`
#  storageManagementPort=`echo ${storageInfo} | grep -o '"management_port".*:.*,' | awk -F':' '{print $2}' | tr -d ', '`
#  storageShutdownURL="http://127.0.0.1:${storageManagementPort}/foglamp/service/shutdown"
#
#  curl -s -X POST ${storageShutdownURL}


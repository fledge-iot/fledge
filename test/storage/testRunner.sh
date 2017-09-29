#!/bin/sh
export IFS=","
testNum=1
n_failed=0
n_passed=0
n_unchecked=0
./testSetup.sh > /dev/null
rm -f failed
rm -rf results
mkdir results
cat testset | while read name method url payload; do
echo -n "Test $testNum ${name}: "
if [ "$payload" = "" ] ; then
	curl -X $method $url -o results/$testNum >/dev/null 2>&1
else
	curl -X $method $url -d@payloads/$payload -o results/$testNum >/dev/null 2>&1
fi
if [ ! -f expected/$testNum ]; then
	n_unchecked=`expr $n_unchecked + 1`
	echo Missing expected results for test $testNum - result unchecked
else
	cmp -s results/$testNum expected/$testNum
	if [ $? -ne "0" ]; then
		echo Failed
		n_failed=`expr $n_failed + 1`
		touch failed
	else
		echo Passed
		n_passed=`expr $n_passed + 1`
	fi
fi
testNum=`expr $testNum + 1`
rm -f tests.result
echo $n_failed Tests Failed >tests.result
echo $n_passed Tests Passed >>tests.result
echo $n_unchecked Tests Unchecked >>tests.result
done
./testCleanup.sh > /dev/null
cat tests.result
rm -f tests.result
if [ -f "failed" ]; then
	exit 1
fi
exit 0

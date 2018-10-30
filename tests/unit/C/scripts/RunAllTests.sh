#!/bin/sh
#set -e
#
# This is the shell script wrapper for running C unit tests
#
if [ "$FOGLAMP_ROOT" = "" ]; then
	echo You must set FOGLAMP_ROOT before running this script
	exit -1
fi
exitstate=0

cd $FOGLAMP_ROOT/tests/unit/C
if [ ! -d results ] ; then
	mkdir results
fi
cmakefile=`find . -name CMakeLists.txt`
for f in $cmakefile; do	
	dir=`dirname $f`
	echo Testing $dir
	(
		cd $dir;
		rm -rf build;
		mkdir build;
		cd build;
		echo Building Tests...;
		cmake ..;
		rc=$?
		if [ $rc != 0 ]; then
			echo cmake failed for $dir;
			exit 1
		fi
		make;
		rc=$?
		if [ $rc != 0 ]; then
			echo make failed for $dir;
			exit 1
		fi
		echo Running tests...;
		./RunTests --gtest_output=xml > /tmp/results;
		rc=$?
		if [ $rc != 0 ]; then
			exit $rc
		fi
	) >/dev/null
	rc=$?
	if [ $rc != 0 ]; then
		echo Tests for $dir failed
		cat /tmp/results
		exitstate=1
	else
		echo All tests in $dir passed
	fi
	file=`echo $dir | sed -e 's#./##' -e 's#/#_#g'`
	mv $dir/build/test_detail.xml results/${file}.xml
done
exit $exitstate

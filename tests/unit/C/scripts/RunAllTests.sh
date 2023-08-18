#!/usr/bin/env bash
#set -e
#
# This is the shell script wrapper for running C unit tests
#
jobs="-j1"
if [[ "$1" == -j* ]]; then
  jobs="$1"
fi
# echo "Using $jobs option for parallel make jobs"

COVERAGE_HTML=0
COVERAGE_XML=0
if [ "$1" = "coverageHtml" ]; then
  COVERAGE_HTML=1
  target="CoverageHtml"
elif [ "$1" = "coverageXml" ]; then
  COVERAGE_XML=1
  target="CoverageXml"
elif [ "$1" = "coverage" ]; then
  echo "Use target 'CoverageHtml' or 'CoverageXml' instead"
  exit 1
fi

if [ "$FLEDGE_ROOT" = "" ]; then
	echo You must set FLEDGE_ROOT before running this script
	exit -1
fi
exitstate=0

cd $FLEDGE_ROOT/tests/unit/C
if [ ! -d results ] ; then
	mkdir results
fi

if [ -f "./CMakeLists.txt" ] ; then
	echo "Compiling libraries..."
	(rm -rf build && mkdir -p build && cd build && cmake -DCMAKE_BUILD_TYPE=Debug .. && make ${jobs} && cd ..) 
	echo "done"
	echo "Looking for StringAround"
	nm lib/libcommon-lib.so.1 | grep StringAround
fi

cmakefile=`find . -name CMakeLists.txt | grep -v "\.\/CMakeLists.txt" `
for f in $cmakefile; do	
	echo "-----------------> Processing $f <-----------------"
	dir=`dirname $f`
	echo Testing $dir
	(
		cd $dir;
		rm -rf build;
		mkdir build;
		cd build;
		echo Building Tests...;
		cmake -DCMAKE_BUILD_TYPE=Debug ..;
		rc=$?
		if [ $rc != 0 ]; then
			echo cmake failed for $dir;
			exit 1
		fi
		make ${jobs} > /dev/null;
		rc=$?
		if [ $rc != 0 ]; then
			echo make failed for $dir;
			exit 1
		fi
		if [ $COVERAGE_HTML -eq 0 ] && [ $COVERAGE_XML -eq 0 ] ; then
			echo Running tests...;
			if [ -f "./RunTests" ] ; then
				./RunTests --gtest_output=xml > /tmp/results;
				rc=$?
				if [ $rc != 0 ]; then
					exit $rc
				fi
			fi
		else
			echo Generating coverage reports...;
			file=$(basename $f)
			# echo "pwd=`pwd`, f=$f, file=$file"
			grep -q ${target} ../${file}
			[ $? -eq 0 ] && (echo Running "make ${target}" && make ${target}) || echo "${target} target not found, skipping..."
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
	source_file=$dir/build/test_detail.xml
	if [ -f "$source_file" ] ; then
		mv $source_file results/${file}.xml
	fi
done
exit $exitstate

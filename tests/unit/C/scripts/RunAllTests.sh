#!/bin/sh
cd $FOGLAMP_ROOT/tests/unit/C
if [ ! -d results ] ; then
	mkdir results
fi
cmakefile=`find . -name CMakeLists.txt`
for f in $cmakefile; do	
	dir=`dirname $f`
	(
		cd $dir;
		rm -rf build;
		mkdir build;
		cd build;
		cmake ..;
		make ;
		./RunTests --gtest_output=xml;
	) > /dev/null
	file=`echo $dir | sed -e 's#./##' -e 's#/#_#g'`
	mv $dir/build/test_detail.xml results/${file}.xml
done

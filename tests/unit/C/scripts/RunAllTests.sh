cmakefile=`find $FOGLAMP_ROOT/tests/unit/C -name CMakeLists.txt`
for f in $cmakefile; do	
	dir=`dirname $f`
	echo $dir
	(
		cd $dir;
		rm -rf build;
		mkdir build;
		cd build;
		cmake ..;
		make ;
		./RunTests --gtest_output=xml;
	) > /dev/null
done
outputs=`find $FOGLAMP_ROOT/tests/unit/C  -name test_detail.xml`
# TODO merge the files in $outputs into a single XML file

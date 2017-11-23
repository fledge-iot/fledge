Storage Engine tests
====================

Run tests against the storage engine and compare to expected results.

Either set FOGLAMP_ROOT to point at the installation to test or pass
the path of the storage service to test in the testRunner.sh command line.

e.g.
	./testRunner.sh ../../../C/services/storafe/build/storage

or
	export FOGLAMP_ROOT=~/foglamp; ./testRunner.sh

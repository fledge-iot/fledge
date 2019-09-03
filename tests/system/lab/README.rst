Scripts to automate FogLAMP Lab

Install git `sudo apt install git`

Copy `tests/system/lab/` to /home/pi/


Typically run in this order:

remove: apt removes all foglamp packages; deletes /usr/local/foglamp; reboots
install: apt update; install foglamp; install gui; install other foglamp packages
setup: curl commands to simulate all gui actions in the lab (except game)
reset: stop foglamp; reset the db and delete any python scripts


Execute `./run` to run test once.
To run the test for 100 iterations or until it fails - execute `./run_until_fails`
#!//usr/bin/env bash

##--------------------------------------------------------------------
## Copyright (c) 2019 Dianomic Systems
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##--------------------------------------------------------------------

##
## Author: Ashish Jabble, Massimiliano Pinto
##


set -e

foglamp_location=`pwd`
is_rhel=`(lsb_release -ds 2>/dev/null || cat /etc/*release 2>/dev/null | head -n1 || uname -om) | egrep '(Red Hat|CentOS)' || echo ""`
if [ "${is_rhel}" != "" ]; then
	echo "Platform is ${is_rhel}"
	sudo yum check-update
	sudo yum update -y
	sudo yum-config-manager --enable 'Red Hat Enterprise Linux Server 7 RHSCL (RPMs)'
	sudo yum install -y @development
	sudo yum install -y boost-devel
	sudo yum install -y glib2-devel
	sudo yum install -y rh-python36
	sudo yum install -y rsyslog
	sudo yum install -y openssl-devel
	sudo yum install -y postgresql-devel
	sudo yum install -y wget
	sudo yum install -y zlib-devel
	sudo yum install -y git
	sudo yum install -y cmake
	sudo yum install -y libuuid-devel
	sudo yum install -y dbus-devel

	sudo su - <<EOF
scl enable rh-python36 bash
pip install dbus-python
EOF
	sudo service rsyslog start

# SQLite3 need to be compiled on CentOS|RHEL 
	if [ -d /tmp/foglamp-sqlite3-pkg ]; then
		rm -rf /tmp/foglamp-sqlite3-pkg 
	fi
	echo "Pulling SQLite3 from FogLAMP SQLite3 repository ..."
	cd /tmp/
	git clone https://github.com/foglamp/foglamp-sqlite3-pkg.git
	cd foglamp-sqlite3-pkg
	cd src
	echo "Compiling SQLite3 static library for FogLAMP ..."
	./configure --enable-shared=false --enable-static=true --enable-static-shell CFLAGS="-DSQLITE_ENABLE_JSON1 -DSQLITE_ENABLE_LOAD_EXTENSION -DSQLITE_ENABLE_COLUMN_METADATA -fno-common -fPIC"
	autoreconf -f -i
	make
	cd $foglamp_location
else
	sudo apt update
	sudo apt -y upgrade

	sudo apt install -y avahi-daemon curl
	sudo apt install -y cmake g++ make build-essential autoconf automake uuid-dev
	sudo apt install -y libtool libboost-dev libboost-system-dev libboost-thread-dev libpq-dev libssl-dev libz-dev
	sudo apt install -y python-dbus python-dev python3-dev python3-pip
	sudo apt install -y sqlite3 libsqlite3-dev
	sudo apt install -y pkg-config
	# sudo apt install -y postgresql
fi

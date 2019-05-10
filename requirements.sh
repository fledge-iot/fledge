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
## Author: Ashish Jabble, Massimiliano Pinto, Vaibhav Singhal
##


set -e

foglamp_location=`pwd`
os_name=`(grep -o '^NAME=.*' /etc/os-release | cut -f2 -d\" | sed 's/"//g')`
os_version=`(grep -o '^VERSION_ID=.*' /etc/os-release | cut -f2 -d\" | sed 's/"//g')`
echo "Platform is ${os_name}, Version: ${os_version}"

if [[ ( $os_name == *"Red Hat"* || $os_name == *"CentOS"* ) &&  $os_version == *"7"* ]]; then
	if [[ $os_name == *"Red Hat"* ]]; then
		yum-config-manager --enable 'Red Hat Enterprise Linux Server 7 RHSCL (RPMs)'
		yum install -y @development
	else
		yum groupinstall "Development tools" -y
		yum install -y centos-release-scl 
	fi
	yum install -y boost-devel
	yum install -y glib2-devel
	yum install -y rh-python36
	yum install -y rsyslog
	yum install -y openssl-devel
	yum install -y postgresql-devel
	yum install -y wget
	yum install -y zlib-devel
	yum install -y git
	yum install -y cmake
	yum install -y libuuid-devel
	yum install -y dbus-devel
	echo "source scl_source enable rh-python36" >> /home/${SUDO_USER}/.bashrc

	su - <<EOF
scl enable rh-python36 bash
pip install dbus-python
EOF
	service rsyslog start

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
	sudo -u $SUDO_USER scl enable rh-python36 bash
elif apt --version 2>/dev/null; then
	apt install -y avahi-daemon curl
	apt install -y cmake g++ make build-essential autoconf automake uuid-dev
	apt install -y libtool libboost-dev libboost-system-dev libboost-thread-dev libpq-dev libssl-dev libz-dev
	apt install -y python-dbus python-dev python3-dev python3-pip
	apt install -y sqlite3 libsqlite3-dev
	apt install -y pkg-config
	# sudo apt install -y postgresql
else
	echo "Requirements cannot be automatically installed, please refer README.rst to install requirements manually"
fi

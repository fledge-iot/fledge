#!/usr/bin/env bash

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

# Upgrades curl to the version related to Fledge
curl_upgrade(){


    if [ -d "${curl_tmp_path}" ]; then
        rm -rf "${curl_tmp_path}"
    fi

    echo "Pulling curl from the Fledge curl repository ..."
    cd /tmp/

    curl -s -L -O "${curl_url}" && \
    unzip -q "${curl_filename}"

    cd "${curl_tmp_path}"

    # curl in RHEL/CentOS is installed in /bin/curl
    # but curl installs by default in /usr/local,
    # so we select the proper target directories
    echo "Building curl ..."
    ./buildconf && \
    ./configure --with-ssl --with-gssapi  --includedir=/usr/include --libdir=/usr/lib64 --bindir=/usr/bin && \
    make && \
    make install
}

# Check if the curl version related to Fledge has been installed
curl_version_check () {

    set +e

    curl_version=$(curl -V | head -n 1)
    curl_version_check=$(echo "${curl_version}" | grep -c "${curl_fledge_version}")

    if (( $curl_version_check >= 1 )); then
        echo "curl version ${curl_fledge_version} installed."
    else
        echo "WARNING: curl version ${curl_fledge_version} not installed, current version :${curl_version}:"
    fi

    set -e
}

# Evaluates the current version of curl and upgrades it if needed
curl_upgrade_evaluates(){

    set +e
    curl_version=$(curl -V | head -n 1)
    curl_version_check=$(echo "${curl_version}" | grep -c "${curl_rhel_version}")
    set -e

    # Evaluates if the curl is the default one and so it needs to be upgraded
    if (( $curl_version_check >= 1 )); then

        echo "curl version ${curl_rhel_version} detected, the standard RHEL/CentOS, upgrading to ${curl_fledge_version}"
        curl_upgrade

        curl_version_check
    else
        echo "A curl version different from the default ${curl_rhel_version} detected, upgrade to a newer one if Fledge make fails."
        echo "version detected :${curl_version}:"

        # Evaluates if the installed version support Kerberos
        curl_kerberos=$(curl -V | grep -ic "Kerberos")
        curl_gssapi=$(curl -V | grep -ic "GSS-API")

        if [[ $curl_kerberos == 0 || curl_gssapi == 0 ]]; then

            echo "WARNING : the curl version detected doesn't support Kerberos."
        fi
    fi

}

# Builds sqlite3 from sources
sqlite3_build_prepare(){

	# SQLite3 build - start
	SQLITE_PKG_REPO_NAME="sqlite3-pkg"
	if [ -d /tmp/${SQLITE_PKG_REPO_NAME} ]; then
		rm -rf /tmp/${SQLITE_PKG_REPO_NAME}
	fi
	echo "Pulling SQLite3 from Dianomic ${SQLITE_PKG_REPO_NAME} repository ..."
	cd /tmp/
	git clone https://github.com/dianomic/${SQLITE_PKG_REPO_NAME}.git ${SQLITE_PKG_REPO_NAME}
	cd ${SQLITE_PKG_REPO_NAME}
	cd src
	echo "Compiling SQLite3 static library for Fledge ..."
	./configure --enable-shared=false --enable-static=true --enable-static-shell CFLAGS="-DSQLITE_MAX_COMPOUND_SELECT=900 -DSQLITE_MAX_ATTACHED=62 -DSQLITE_ENABLE_JSON1 -DSQLITE_ENABLE_LOAD_EXTENSION -DSQLITE_ENABLE_COLUMN_METADATA -fno-common -fPIC"
	autoreconf -f -i
}


# Variables for curl upgrade, if needed
curl_filename="curl-7.65.3"
curl_url="https://github.com/curl/curl/releases/download/curl-7_65_3/${curl_filename}.zip"
curl_tmp_path="/tmp/${curl_filename}"
curl_fledge_version="7.65.3"
curl_rhel_version="7.29"

fledge_location=`pwd`
os_name=`(grep -o '^NAME=.*' /etc/os-release | cut -f2 -d\" | sed 's/"//g')`
os_version=`(grep -o '^VERSION_ID=.*' /etc/os-release | cut -f2 -d\" | sed 's/"//g')`
echo "Platform is ${os_name}, Version: ${os_version}"

if [[ ( $os_name == *"Red Hat"* || $os_name == *"CentOS"* ) &&  $os_version == *"7"* ]]; then
	if [[ $os_name == *"Red Hat"* ]]; then
		yum-config-manager --enable 'Red Hat Software Collections RPMs for Red Hat Enterprise Linux 7 Server from RHUI'
		yum install -y @development
	else
		yum groupinstall "Development tools" -y
		yum install -y centos-release-scl
	fi
	yum install -y boost-devel
	yum install -y glib2-devel
	yum install -y rsyslog
	yum install -y openssl-devel
	yum install -y rh-python36
	yum install -y rh-postgresql96
	yum install -y rh-postgresql96-postgresql-devel
	yum install -y wget
	yum install -y zlib-devel
	yum install -y git
	yum install -y cmake
	yum install -y libuuid-devel
	# for Kerberos authentication
	yum install -y krb5-workstation
	yum install -y curl-devel

	echo "source scl_source enable rh-python36" >> /home/${SUDO_USER}/.bashrc
	service rsyslog start

    sqlite3_build_prepare

	# Attempts a second execution of make if the first fails
	set +e
	make
	exit_code=$?
	if [[ $exit_code != 0 ]]; then

		set -e
		make
	fi
	cd $fledge_location
	set -e

	# Upgrade curl if needed
	curl_upgrade_evaluates

	cd $fledge_location

	# To avoid to stop the execution for any internal error of scl_source
	set +e
	source scl_source enable rh-python36
	set -e

	#
	# A gcc version newer than 4.9.0 is needed to properly use <regex>
	# the installation of these packages will not overwrite the previous compiler
	# the new one will be available using the command 'source scl_source enable devtoolset-7'
	# the previous gcc will be enabled again after a log-off/log-in.
	#
	yum install -y yum-utils
	yum-config-manager --enable rhel-server-rhscl-7-rpms
	yum install -y devtoolset-7

	# To avoid to stop the execution for any internal error of scl_source
	set +e
	source scl_source enable devtoolset-7
	set -e

elif apt --version 2>/dev/null; then
	# avoid interactive questions
	DEBIAN_FRONTEND=noninteractive apt install -yq libssl-dev

	apt install -y avahi-daemon ca-certificates curl
	apt install -y cmake g++ make build-essential autoconf automake uuid-dev
	apt install -y libtool libboost-dev libboost-system-dev libboost-thread-dev libpq-dev libz-dev
	apt install -y python-dev python3-dev python3-pip

    sqlite3_build_prepare
    make

	apt install -y pkg-config

	# for Kerberos authentication, avoid interactive questions
	DEBIAN_FRONTEND=noninteractive apt install -yq krb5-user
	DEBIAN_FRONTEND=noninteractive apt install -yq libcurl4-openssl-dev

	apt install -y cpulimit
	# apt install -y postgresql
else
	echo "Requirements cannot be automatically installed, please refer README.rst to install requirements manually"
fi

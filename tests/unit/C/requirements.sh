#!/usr/bin/env bash

##--------------------------------------------------------------------
## Copyright (c) 2025 Dianomic Systems
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
## Author: Ashwini Kumar Pandey, Ashish Jabble
##

set -e

OS_NAME=$(grep -oP '^NAME="\K[^"]+' /etc/os-release)
OS_VERSION=$(grep -oP '^VERSION_ID="\K[^"]+' /etc/os-release)
OS_CODENAME=$(grep -oP '^VERSION_CODENAME=\K.*' /etc/os-release)
# Function to install and build Google Test from package
install_gtest_from_package() {
    echo "Installing Google Test via package manager..."

    # Install the libgtest-dev package
    sudo apt-get install -y libgtest-dev

    echo "Building Google Test libraries manually..."
    cd /usr/src/gtest
    sudo cmake -E make_directory build
    sudo cmake -E chdir build cmake ..
    sudo cmake --build build

    if [[ "${OS_VERSION}" == "18.04" || "${OS_CODENAME}" == "buster" ]]; then
        sudo cp build/libgtest* /usr/lib
    else
        sudo cp build/lib/libgtest* /usr/lib
    fi
    echo "Google Test has been successfully installed."
}

# Function to build and install Google Test from source
install_gtest_from_source() {
    echo "Installing Google Test via source..."

    # Define repository name and branch
    local GTEST_REPO_NAME="googletest"
    local GTEST_BRANCH="${1:-release-1.11.0}"  # Default branch is release-1.11.0

    # Clean up any existing directory
    if [ -d "/tmp/${GTEST_REPO_NAME}" ]; then
        echo "Removing existing ${GTEST_REPO_NAME} directory in /tmp..."
        sudo rm -rf "/tmp/${GTEST_REPO_NAME}"
    fi

    # Clone the Google Test repository
    echo "Cloning Google Test repository (${GTEST_BRANCH})..."
    git clone https://github.com/google/${GTEST_REPO_NAME}.git --branch "${GTEST_BRANCH}" --depth 1 -q "/tmp/${GTEST_REPO_NAME}"

    # Build and install Google Test
    cd "/tmp/${GTEST_REPO_NAME}"
    mkdir -p build && cd build
    echo "Configuring and building Google Test..."
    cmake .. -DBUILD_GMOCK=OFF > /dev/null
    make -j$(nproc) > /dev/null
    sudo make install > /dev/null

    echo "Google Test installation complete for Ubuntu 24.04 or later!"
}

# Function to install Google Test for Red Hat-based distributions
install_gtest_rhel() {
    echo "Installing Google Test for Red Hat-based distributions..."

    # Install required packages
    sudo yum install -y gtest gtest-devel

    echo "Google Test installation complete for Red Hat-based distributions!"
}

# Function to detect the platform and execute the appropriate installation
detect_and_install_gtest() {
    echo "Detected Platform: ${OS_NAME}, Version: ${OS_VERSION}"
    # Install based on detected OS
    if [[ ${OS_NAME,,} == "red hat"* ]] || [[ ${OS_NAME,,} == "centos"* ]]; then
        install_gtest_rhel
    elif [[ ${OS_NAME,,} == "ubuntu" ]]; then
        if [[ $(echo "${OS_VERSION} >= 24.04" | bc -l) -eq 1 ]]; then
            install_gtest_from_source
        else
            install_gtest_from_package
        fi
    else
        install_gtest_from_package
    fi
}

# Main execution
detect_and_install_gtest
echo "Google Test installation process completed successfully!"
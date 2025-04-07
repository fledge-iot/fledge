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
## Author: Ashwini Kumar Pandey
##

set -e

# Builds Google Test from sources
gtest_build_prepare() {

    # Define the repository name and branch
    GTEST_REPO_NAME="googletest"
    GTEST_BRANCH="release-1.11.0"

    # Clean up any existing directory
    if [ -d /tmp/${GTEST_REPO_NAME} ]; then
        echo "Removing existing ${GTEST_REPO_NAME} directory in /tmp..."
        rm -rf /tmp/${GTEST_REPO_NAME}
    fi

    # Clone the Google Test repository
    echo "Cloning Google Test ${GTEST_BRANCH} branch from repository..."
    cd /tmp/
    git clone https://github.com/google/${GTEST_REPO_NAME}.git --branch=${GTEST_BRANCH}

    # Navigate to the cloned repository
    cd ${GTEST_REPO_NAME}

    # Create and navigate to a build directory
    mkdir -p build
    cd build

    # Configure and compile the project
    echo "Configuring and building Google Test..."
    cmake .. -DBUILD_GMOCK=ON -DBUILD_GTEST=ON
    make -j$(nproc)

    # Install the compiled binaries (optional)
    echo "Installing Google Test..."
    sudo make install

    echo "Google Test build and installation complete!"
}

# Execute the build function
gtest_build_prepare
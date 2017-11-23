
###############################################################################
################################### COMMANDS ##################################
###############################################################################
MKDIR_PATH := mkdir -p
CD := cd
LN := ln -sf
CMAKE := cmake
PIP_USER_FLAG = --user
PIP_INSTALL_REQUIREMENTS := pip3 install -Ir
PYTHON_BUILD_PACKAGE = python3 setup.py build -b ../$(PYTHON_BUILD_DIR)
RM_DIR := rm -r
RM_FILE := rm
MAKE_INSTALL = $(MAKE) install
CP_DIR := cp -r

###############################################################################
################################### DIRS/FILES ################################
###############################################################################
# PARENT DIR
MKFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_DIR := $(dir $(MKFILE_PATH))

# C BUILD DIRS/FILES
CMAKE_FILE := $(CURRENT_DIR)/CMakeLists.txt
CMAKE_BUILD_DIR := cmake_build
CMAKE_GEN_MAKEFILE := $(CURRENT_DIR)/$(CMAKE_BUILD_DIR)/Makefile
CMAKE_SERVICES_DIR := $(CURRENT_DIR)/$(CMAKE_BUILD_DIR)/C/services
CMAKE_STORAGE_BINARY := $(CMAKE_SERVICES_DIR)/storage/storage
CMAKE_PLUGINS_DIR := $(CURRENT_DIR)/$(CMAKE_BUILD_DIR)/C/plugins
DEV_SERVICES_DIR := $(CURRENT_DIR)/services
SYMLINK_PLUGINS_DIR := $(CURRENT_DIR)/plugins
SYMLINK_STORAGE_BINARY := $(DEV_SERVICES_DIR)/storage

# PYTHON BUILD DIRS/FILES
PYTHON_SRC_DIR := python
PYTHON_BUILD_DIR := python_build
PYTHON_LIB_DIR := $(PYTHON_BUILD_DIR)/lib
PYTHON_REQUIREMENTS_FILE := $(PYTHON_SRC_DIR)/requirements.txt
PYTHON_SETUP_FILE := $(PYTHON_SRC_DIR)/setup.py

# INSTALL DIRS
INSTALL_DIR=$(DESTDIR)/usr/local/foglamp
PYTHON_INSTALL_DIR=$(INSTALL_DIR)/python

###############################################################################
################################### OTHER VARS ################################
###############################################################################
# ETC
PACKAGE_NAME=FogLAMP

###############################################################################
############################ PRIMARY TARGETS ##################################
###############################################################################
# default
# compile any code that must be compiled
# generally prepare the development tree to allow for core to be run
default : c_build $(SYMLINK_STORAGE_BINARY) $(SYMLINK_PLUGINS_DIR) python_build python_requirements_user

# install
# Creates a deployment structure in the default destination, /usr/local/foglamp
# Destination may be overridden by use of the DESTDIR=<location> directive
# This first does a make to build anything needed for the installation.
install : $(INSTALL_DIR) c_install python_install python_requirements

############################ C BUILD/INSTALL TARGETS ##########################
###############################################################################
# run make execute makefiles producer by cmake
c_build : $(CMAKE_GEN_MAKEFILE)
	$(CD) $(CMAKE_BUILD_DIR) ; $(MAKE)

# run cmake to generate makefiles
# always rerun cmake because:
#   parent CMakeLists.txt may have changed
#   CMakeLists.txt files in subdirectories may have changed
$(CMAKE_GEN_MAKEFILE) : $(CMAKE_FILE) $(CMAKE_BUILD_DIR)
	$(CD) $(CMAKE_BUILD_DIR) ; $(CMAKE) $(CURRENT_DIR)

# create build dir
$(CMAKE_BUILD_DIR) :
	$(MKDIR_PATH) $@

# create symlink to storage binary
$(SYMLINK_STORAGE_BINARY) : $(DEV_SERVICES_DIR)
	$(LN) $(CMAKE_STORAGE_BINARY) $(SYMLINK_STORAGE_BINARY)

# create services dir
$(DEV_SERVICES_DIR) :
	$(MKDIR_PATH) $(DEV_SERVICES_DIR)

# create symlink for plugins dir
$(SYMLINK_PLUGINS_DIR) :
	$(LN) $(CMAKE_PLUGINS_DIR) $(SYMLINK_PLUGINS_DIR)

# run make install on cmake based components
c_install : c_build
	$(CD) $(CMAKE_BUILD_DIR) ; $(MAKE_INSTALL)

###############################################################################
###################### PYTHON BUILD/INSTALL TARGETS ###########################
###############################################################################
# build python source
python_build : $(PYTHON_SETUP_FILE)
	cd $(PYTHON_SRC_DIR) ; $(PYTHON_BUILD_PACKAGE)

# install python requirements without --user 
python_requirements : $(PYTHON_REQUIREMENTS_FILE)
	$(PIP_INSTALL_REQUIREMENTS) $(PYTHON_REQUIREMENTS_FILE)

# install python requirements for user
python_requirements_user : $(PYTHON_REQUIREMENTS_FILE)
	$(PIP_INSTALL_REQUIREMENTS) $(PYTHON_REQUIREMENTS_FILE) $(PIP_USER_FLAG)

# create python install dir
$(PYTHON_INSTALL_DIR) :
	$(MKDIR_PATH) $@

# copy python package into install dir
python_install : python_build $(PYTHON_INSTALL_DIR)
	$(CP_DIR) $(PYTHON_LIB_DIR)/* $(PYTHON_INSTALL_DIR)

###############################################################################
######################## SUPPORTING BUILD/INSTALL TARGETS #####################
###############################################################################
# create install directory
$(INSTALL_DIR) : 
	$(MKDIR_PATH) $@

###############################################################################
###############################################################################
###################### CLEAN/UNINSTALL TARGETS ################################
###############################################################################
# clean
clean :
	-$(RM_DIR) $(CMAKE_BUILD_DIR)
	-$(RM_DIR) $(PYTHON_BUILD_DIR)
	-$(RM_DIR) $(DEV_SERVICES_DIR)
	-$(RM) $(SYMLINK_PLUGINS_DIR)


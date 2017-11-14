# COMMANDS
MKDIR := mkdir
CD := cd
LN := ln -sf
CMAKE := cmake
PIP_INSTALL_REQUIREMENTS := pip3 install --user -Ur
PIP_INSTALL_PACKAGE := pip3 install --user -e
PIP_UNINSTALL_PACKAGE := pip3 uninstall -y

# PARENT DIR
MKFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_DIR := $(dir $(MKFILE_PATH))

# C BUILD DIRS/FILES
CMAKE_BUILD_DIR := cmake_build
CMAKE_GEN_MAKEFILE := $(CURRENT_DIR)/$(CMAKE_BUILD_DIR)/Makefile
CMAKE_SERVICES_DIR := $(CURRENT_DIR)/$(CMAKE_BUILD_DIR)/src/C/services
CMAKE_PLUGINS_DIR := $(CURRENT_DIR)/$(CMAKE_BUILD_DIR)/src/C/plugins
SYMLINK_SERVICES_DIR := $(CURRENT_DIR)/services
SYMLINK_PLUGINS_DIR := $(CURRENT_DIR)/plugins

# PYTHON BUILD DIRS/FILES
PYTHON_DIR := python
PYTHON_REQUIREMENTS_FILE := $(PYTHON_DIR)/requirements.txt

# ETC
PACKAGE_NAME=FogLAMP

# TARGETS
# compile any code that must be compiled and generally prepare the development tree to allow for core to be run
default : c_build $(SYMLINK_SERVICES_DIR) $(SYMLINK_PLUGINS_DIR) python_build

# create symlink for plugins dir
$(SYMLINK_PLUGINS_DIR) :
	$(LN) $(CMAKE_PLUGINS_DIR) $(SYMLINK_PLUGINS_DIR)

# create symlink for services dir
$(SYMLINK_SERVICES_DIR) :
	$(LN) $(CMAKE_SERVICES_DIR) $(SYMLINK_SERVICES_DIR)

# create build dir
$(CMAKE_BUILD_DIR) :
	-$(MKDIR) $@

# run cmake to generate makefiles
$(CMAKE_GEN_MAKEFILE) : $(CMAKE_BUILD_DIR)
	$(CD) $(CMAKE_BUILD_DIR) ; $(CMAKE) $(CURRENT_DIR)

# run make execute makefiles producer by cmake
c_build : $(CMAKE_GEN_MAKEFILE)
	$(CD) $(CMAKE_BUILD_DIR) ; $(MAKE)

# install python requirements
python_requirements : $(PYTHON_REQUIREMENTS_FILE)
	$(PIP_INSTALL_REQUIREMENTS) $(PYTHON_REQUIREMENTS_FILE)

# install python FogLAMP package
python_build : python_requirements 
	$(PIP_INSTALL_PACKAGE) $(PYTHON_DIR)

# clean
clean : 
	-rm -r $(CMAKE_BUILD_DIR)
	-rm $(SYMLINK_SERVICES_DIR)
	-rm $(SYMLINK_PLUGINS_DIR)
	-pip3 uninstall -y $(PACKAGE_NAME)



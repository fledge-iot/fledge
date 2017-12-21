
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
CP     := cp
CP_DIR := cp -r

###############################################################################
################################### DIRS/FILES ################################
###############################################################################
# PARENT DIR
MKFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_DIR := $(dir $(MKFILE_PATH))

# C BUILD DIRS/FILES
CMAKE_FILE             := $(CURRENT_DIR)/CMakeLists.txt
CMAKE_BUILD_DIR        := cmake_build
CMAKE_GEN_MAKEFILE     := $(CURRENT_DIR)/$(CMAKE_BUILD_DIR)/Makefile
CMAKE_SERVICES_DIR     := $(CURRENT_DIR)/$(CMAKE_BUILD_DIR)/C/services
CMAKE_STORAGE_BINARY   := $(CMAKE_SERVICES_DIR)/storage/storage
CMAKE_PLUGINS_DIR      := $(CURRENT_DIR)/$(CMAKE_BUILD_DIR)/C/plugins
DEV_SERVICES_DIR       := $(CURRENT_DIR)/services
SYMLINK_PLUGINS_DIR    := $(CURRENT_DIR)/plugins
SYMLINK_STORAGE_BINARY := $(DEV_SERVICES_DIR)/storage

# PYTHON BUILD DIRS/FILES
PYTHON_SRC_DIR := python
PYTHON_BUILD_DIR := python_build
PYTHON_LIB_DIR := $(PYTHON_BUILD_DIR)/lib
PYTHON_REQUIREMENTS_FILE := $(PYTHON_SRC_DIR)/requirements.txt
PYTHON_SETUP_FILE := $(PYTHON_SRC_DIR)/setup.py

# DATA AND ETC DIRS/FILES
DATA_SRC_DIR := data

# INSTALL DIRS
INSTALL_DIR=$(DESTDIR)/usr/local/foglamp
PYTHON_INSTALL_DIR=$(INSTALL_DIR)/python
SCRIPTS_INSTALL_DIR=$(INSTALL_DIR)/scripts
BIN_INSTALL_DIR=$(INSTALL_DIR)/bin
EXTRAS_INSTALL_DIR=$(INSTALL_DIR)/extras
SCRIPT_COMMON_INSTALL_DIR = $(SCRIPTS_INSTALL_DIR)/common
SCRIPT_PLUGINS_STORAGE_INSTALL_DIR = $(SCRIPTS_INSTALL_DIR)/plugins/storage
SCRIPT_SERVICES_INSTALL_DIR = $(SCRIPTS_INSTALL_DIR)/services
SCRIPT_TASKS_INSTALL_DIR = $(SCRIPTS_INSTALL_DIR)/tasks
FOGBENCH_PYTHON_INSTALL_DIR = $(EXTRAS_INSTALL_DIR)/python

# SCRIPTS TO INSTALL IN BIN DIR
FOGBENCH_SCRIPT_SRC        := scripts/extras/fogbench
FOGLAMP_SCRIPT_SRC         := scripts/foglamp

# SCRIPTS TO INSTALL IN SCRIPTS DIR
COMMON_SCRIPTS_SRC         := scripts/common
POSTGRES_SCRIPT_SRC        := scripts/plugins/storage/postgres
SOUTH_SCRIPT_SRC           := scripts/services/south
STORAGE_SERVICE_SCRIPT_SRC := scripts/services/storage
STORAGE_SCRIPT_SRC         := scripts/storage
NORTH_SCRIPT_SRC           := scripts/tasks/north
PURGE_SCRIPT_SRC           := scripts/tasks/purge
STATISTICS_SCRIPT_SRC      := scripts/tasks/statistics
BACKUP_POSTGRES            := scripts/tasks/backup_postgres
RESTORE_POSTGRES           := scripts/tasks/restore_postgres


# FOGBENCH 
FOGBENCH_PYTHON_SRC_DIR    := extras/python/fogbench

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
default : c_build $(SYMLINK_STORAGE_BINARY) $(SYMLINK_PLUGINS_DIR) \
	python_build python_requirements_user

# install
# Creates a deployment structure in the default destination, /usr/local/foglamp
# Destination may be overridden by use of the DESTDIR=<location> directive
# This first does a make to build anything needed for the installation.
install : $(INSTALL_DIR) \
	c_install \
	python_install \
	python_requirements \
	scripts_install \
	bin_install \
	extras_install \
	data_install

###############################################################################
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
	$(CD) $(PYTHON_SRC_DIR) ; $(PYTHON_BUILD_PACKAGE)

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
###################### SCRIPTS INSTALL TARGETS ################################
###############################################################################
# install scripts
scripts_install : $(SCRIPTS_INSTALL_DIR) \
	install_common_scripts \
	install_postgres_script \
	install_south_script \
	install_storage_service_script \
	install_north_script \
	install_purge_script \
	install_statistics_script \
	install_storage_script \
	install_backup_postgres_script \
	install_restore_postgres_script \

# create scripts install dir
$(SCRIPTS_INSTALL_DIR) :
	$(MKDIR_PATH) $@

install_common_scripts : $(SCRIPT_COMMON_INSTALL_DIR) $(COMMON_SCRIPTS_SRC)
	$(CP) $(COMMON_SCRIPTS_SRC)/*.sh $(SCRIPT_COMMON_INSTALL_DIR)
	
install_postgres_script : $(SCRIPT_PLUGINS_STORAGE_INSTALL_DIR) $(POSTGRES_SCRIPT_SRC)
	$(CP) $(POSTGRES_SCRIPT_SRC) $(SCRIPT_PLUGINS_STORAGE_INSTALL_DIR)
	
install_south_script : $(SCRIPT_SERVICES_INSTALL_DIR) $(SOUTH_SCRIPT_SRC)
	$(CP) $(SOUTH_SCRIPT_SRC) $(SCRIPT_SERVICES_INSTALL_DIR)

install_storage_service_script : $(SCRIPT_SERVICES_INSTALL_DIR) $(STORAGE_SERVICE_SCRIPT_SRC)
	$(CP) $(STORAGE_SERVICE_SCRIPT_SRC) $(SCRIPT_SERVICES_INSTALL_DIR)

install_north_script : $(SCRIPT_TASKS_INSTALL_DIR) $(NORTH_SCRIPT_SRC)
	$(CP) $(NORTH_SCRIPT_SRC) $(SCRIPT_TASKS_INSTALL_DIR)

install_purge_script : $(SCRIPT_TASKS_INSTALL_DIR) $(PURGE_SCRIPT_SRC)
	$(CP) $(PURGE_SCRIPT_SRC) $(SCRIPT_TASKS_INSTALL_DIR)

install_statistics_script : $(SCRIPT_TASKS_INSTALL_DIR) $(STATISTICS_SCRIPT_SRC)
	$(CP) $(STATISTICS_SCRIPT_SRC) $(SCRIPT_TASKS_INSTALL_DIR)

install_backup_postgres_script : $(SCRIPT_TASKS_INSTALL_DIR) $(BACKUP_POSTGRES)
	$(CP) $(BACKUP_POSTGRES) $(SCRIPT_TASKS_INSTALL_DIR)

install_restore_postgres_script : $(SCRIPT_TASKS_INSTALL_DIR) $(RESTORE_POSTGRES)
	$(CP) $(RESTORE_POSTGRES) $(SCRIPT_TASKS_INSTALL_DIR)

install_storage_script : $(SCRIPT_INSTALL_DIR) $(STORAGE_SCRIPT_SRC)
	$(CP) $(STORAGE_SCRIPT_SRC) $(SCRIPTS_INSTALL_DIR)

$(SCRIPT_COMMON_INSTALL_DIR) :
	$(MKDIR_PATH) $@

$(SCRIPT_PLUGINS_STORAGE_INSTALL_DIR) :
	$(MKDIR_PATH) $@

$(SCRIPT_SERVICES_INSTALL_DIR) :
	$(MKDIR_PATH) $@

$(SCRIPT_STORAGE_INSTALL_DIR) :
	$(MKDIR_PATH) $@

$(SCRIPT_TASKS_INSTALL_DIR) :
	$(MKDIR_PATH) $@

###############################################################################
########################## BIN INSTALL TARGETS ################################
###############################################################################
# install bin
bin_install : $(BIN_INSTALL_DIR) $(FOGBENCH_SCRIPT_SRC) $(FOGLAMP_SCRIPT_SRC)
	$(CP) $(FOGBENCH_SCRIPT_SRC) $(BIN_INSTALL_DIR)
	$(CP) $(FOGLAMP_SCRIPT_SRC) $(BIN_INSTALL_DIR)

# create bin install dir
$(BIN_INSTALL_DIR) :
	$(MKDIR_PATH) $@

###############################################################################
####################### EXTRAS INSTALL TARGETS ################################
###############################################################################
# install bin
extras_install : $(EXTRAS_INSTALL_DIR) install_python_fogbench

install_python_fogbench : $(FOGBENCH_PYTHON_INSTALL_DIR) $(FOGBENCH_PYTHON_SRC_DIR)
	$(CP_DIR) $(FOGBENCH_PYTHON_SRC_DIR) $(FOGBENCH_PYTHON_INSTALL_DIR)

$(FOGBENCH_PYTHON_INSTALL_DIR) :
	$(MKDIR_PATH) $@

# create extras install dir
$(EXTRAS_INSTALL_DIR) :
	$(MKDIR_PATH) $@

###############################################################################
####################### DATA INSTALL TARGETS ################################
###############################################################################
# install data
data_install : $(DATA_INSTALL_DIR) install_data

install_data : $(DATA_INSTALL_DIR) $(DATA_SRC_DIR)
	$(CP_DIR) $(DATA_SRC_DIR) $(INSTALL_DIR)

# data and etc directories, should be owned by the user running foglamp
# If install is executed with sudo and the sudo user is root, the data and etc
# directories must be set to be owned by the calling user.
ifdef SUDO_USER
ifeq ("$(USER)","root")
	chown -R ${SUDO_USER}:${SUDO_USER} $(INSTALL_DIR)/$(DATA_SRC_DIR)
endif
endif

# create extras install dir
#$(DATA_INSTALL_DIR) :
#	$(MKDIR_PATH) $@

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


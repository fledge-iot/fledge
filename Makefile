
storage_service_build_dir = './C/services/storage/build/'
# TODO: verify that this is okay
# storage
storage_service : 
	echo "storage service"
	echo $(storage_service_build_dir)
	mkdir -p $(storage_service_build_dir)
	cd $(storage_service_build_dir) ; cmake .. ; make

postgres_plugin_build_dir = './C/plugins/storage/postgres/build/'
postgresql_plugin:
	echo "postgresql plugin"
	echo $(postgres_plugin_build_dir)
	mkdir -p $(postgres_plugin_build_dir)
	cd $(postgres_plugin_build_dir) ; cmake .. ; make

# TODO: we have foglamp package AND all dependencies
# TODO: do we have any plans to put our python package into PyPi? https://packaging.python.org/glossary/#term-python-package-index-pypi
foglamp_python_package_dir = './python/'
foglamp_python_package : 
	echo "foglamp python package"
	echo $(foglamp_python_package_dir)
	cd $(foglamp_python_package_dir) ; python3 setup.py sdist --dist-dir=./build


#default - e.g. simple make with no arguments
#Compiles any code that must be compiled and general prepares the development tree to allow the Core to be run.
default :
	echo "default"

#install
#Creates a deployment structure in the default destination, /usr/local. Destination may be overridden by use of the DESTDIR=<location> directive. This first does a make to build anything needed for the installation.
install :
	echo "install"

#clean
#Return the source tree to the state it would be in after a checkout, i.e. remove anything built as a consequence of the execution of make
clean : 
	echo "clean"

#snap
#Make the deployment structure, building whatever is necessary (e.g. doing a make) and then create a snap package from it.
snap : 
	echo "snap"

#docker
#Create a deployment structure (e.g. run make) and then create a docker file that can be used to create a docker container that will run FogLAMP
docker : 
	echo "docker"

#doc
#Generate the FogLAMP documentation
doc : 
	echo "doc"


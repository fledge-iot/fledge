#!/bin/bash

##--------------------------------------------------------------------
## Copyright (c) 2019 OSIsoft, LLC
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

__author__="Stefano Simonelli"
__version__="1.0"

# Identifies the platform on which FogLAMP reside
# output :
#          not empty - Centos or RedHat
#          empty     - Debian/Ubuntu
get_platform() {

	(lsb_release -ds 2>/dev/null || cat /etc/*release 2>/dev/null | head -n1 || uname -om)

}

#!/usr/bin/env bash

############################################################
#
# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
############################################################

__author__="${FULL_NAME}"
__copyright__="Copyright (c) 2017 OSIsoft, LLC"
__license__="Apache 2.0"
__version__="${VERSION}"


# DB setup
jenkins_db_user='jenkins'
foglamp_db_user='foglamp'
postgres_db_user='postgres'

PGPASSWORD=${postgres_db_user} psql -U ${postgres_db_user} -h localhost -f src/sql/foglamp_ddl.sql ${postgres_db_user}
PGPASSWORD=${foglamp_db_user} psql -U ${foglamp_db_user} -h localhost -f src/sql/foglamp_init_data.sql ${foglamp_db_user}
PGPASSWORD=${foglamp_db_user} psql -c "GRANT ALL ON DATABASE ${foglamp_db_user} to ${jenkins_db_user};" -U ${foglamp_db_user} -h localhost
PGPASSWORD=${foglamp_db_user} psql -c "GRANT ALL ON SCHEMA ${foglamp_db_user} to ${jenkins_db_user};" -U ${foglamp_db_user} -h localhost
PGPASSWORD=${foglamp_db_user} psql -c "ALTER ROLE ${jenkins_db_user} IN DATABASE ${foglamp_db_user} SET search_path = ${foglamp_db_user};" -U ${foglamp_db_user} -h localhost
PGPASSWORD=${foglamp_db_user} psql -c "GRANT ALL ON ALL TABLES IN SCHEMA ${foglamp_db_user} TO ${jenkins_db_user};" -U ${foglamp_db_user} -h localhost

# Change directory
cd src/python

# clean
rm -rf venv
source build.sh -c

# pylint
source build.sh -l

# python tests
source build.sh -p
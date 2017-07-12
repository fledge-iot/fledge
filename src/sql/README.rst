Installing
==========

Run the following commands from the shell:: 
    PGPASSWORD=postgres psql -U postgres -h localhost -f foglamp_ddl.sql postgres
    PGPASSWORD=foglamp psql -U foglamp -h localhost -f foglamp_init_data.sql foglamp 


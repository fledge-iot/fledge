Installing
==========

.. code-block:: python
    PGPASSWORD=postgres psql -U postgres -h localhost -f foglamp_ddl.sql postgres
    PGPASSWORD=foglamp psql -U foglamp -h localhost -f foglamp_init_data.sql foglamp 


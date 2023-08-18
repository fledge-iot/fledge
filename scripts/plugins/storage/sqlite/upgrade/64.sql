-- Create control_api table
CREATE TABLE fledge.control_api (
             name             character  varying(255)     NOT NULL                 ,       -- control API name
             description      character  varying(255)     NOT NULL                 ,       -- description of control API
             type             integer                     NOT NULL                 ,       -- 0 for write and 1 for operation
             operation_name   character  varying(255)                              ,       -- name of the operation and only valid if type is operation
             destination      integer                     NOT NULL                 ,       -- destination of request; 0-broadcast, 1-service, 2-asset, 3-script
             destination_arg  character  varying(255)                              ,       -- name of the destination and only used if destination is non-zero
             anonymous        boolean                     NOT NULL DEFAULT  'f'    ,       -- anonymous callers to make request to control API; by default false
             CONSTRAINT       control_api_pname           PRIMARY KEY (name)
             );

-- Create control_api_parameters table
CREATE TABLE fledge.control_api_parameters (
             name             character  varying(255)     NOT NULL                 ,       -- foreign key to fledge.control_api
             parameter        character  varying(255)     NOT NULL                 ,       -- name of parameter
             value            character  varying(255)                              ,       -- value of parameter if constant otherwise default
             constant         boolean                     NOT NULL                 ,       -- parameter is either a constant or variable
             FOREIGN KEY (name) REFERENCES control_api (name)
             );

-- Create control_api_acl table
CREATE TABLE fledge.control_api_acl (
             name             character  varying(255)     NOT NULL                 ,       -- foreign key to fledge.control_api
             user             character  varying(255)     NOT NULL                 ,       -- foreign key to fledge.users
             FOREIGN KEY (name) REFERENCES control_api (name)                      ,
             FOREIGN KEY (user) REFERENCES users (uname)
             );

-- Roles
INSERT INTO fledge.roles ( name, description )
     VALUES ('view', 'Only to view the configuration'),
            ('data-view', 'Only read the data in buffer');
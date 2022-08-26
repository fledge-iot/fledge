-- Access Control List usage relation
CREATE TABLE fledge.acl_usage (
             name            character varying(255)  NOT NULL,  -- ACL name
             entity_type     character varying(80)   NOT NULL,  -- associated entity type: service or script 
             entity_name     character varying(255)  NOT NULL,  -- associated entity name
             CONSTRAINT      usage_acl_pkey          PRIMARY KEY (name, entity_type, entity_name) );

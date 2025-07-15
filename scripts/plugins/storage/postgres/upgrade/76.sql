INSERT INTO fledge.configuration ( key, display_name, description, value )
     VALUES ( 'SUPPORT_BUNDLE',
              'Support Bundle',
              'Support Bundle Configuration',
              '{"auto_support_bundle":{"description": "Automatically create support bundle when service fails","type": "boolean","default": "true","displayName": "Auto Generate On Failure","value":"true"},"support_bundle_retain_count":{"description": "Number of support bundles to retain (minimum 1)","type": "integer","default": "3","minimum": "1","displayName": "Bundles To Retain","value":"3"}}'
            );

INSERT INTO fledge.category_children (parent, child) VALUES ('Advanced', 'SUPPORT_BUNDLE');


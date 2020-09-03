#!/bin/bash

# Include logging
. $FLEDGE_ROOT/scripts/common/write_log.sh

# Logger wrapper
schema_update_log() {
    write_log "Downgrade" "scripts.plugins.storage.${PLUGIN_NAME}.schema_update" "$1" "$2" "$3" "$4"
}

schema_update_log "debug" "Downgrade not supported. Exiting" "all" "pretty"
exit 1

#!/bin/bash

# Set FLEDGE_ROOT properly so that Fledge logfiles may be setup correctly in this script
sed "s|\$FLEDGE_ROOT|${FLEDGE_ROOT}|g" fledge_logger.conf > /tmp/fledge_logger.conf.out
sed "s|\$FLEDGE_ROOT|${FLEDGE_ROOT}|g" fledge_logrotate.conf > /tmp/fledge_logrotate.conf.out

sudo mv /tmp/fledge_logger.conf.out /etc/rsyslog.d/fledge.conf
sudo mv /tmp/fledge_logrotate.conf.out /etc/logrotate.d/fledge

sudo chmod 644 /etc/rsyslog.d/fledge.conf /etc/logrotate.d/fledge
sudo chown -R root:root /etc/rsyslog.d/fledge.conf /etc/logrotate.d/fledge
sudo chown -R root:syslog ${FLEDGE_ROOT}/data/logs

sudo systemctl restart rsyslog.service


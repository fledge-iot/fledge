#!/bin/bash

# Set FLEDGE_ROOT properly so that Fledge logfiles may be setup correctly in this script
sed "s|\$FLEDGE_ROOT|${FLEDGE_ROOT}|g" rsyslog.conf > /tmp/rsyslog.conf.out
sed "s|\$FLEDGE_ROOT|${FLEDGE_ROOT}|g" logrotate.conf > /tmp/logrotate.conf.out

sudo mv /tmp/rsyslog.conf.out /etc/rsyslog.d/fledge.conf
sudo mv /tmp/logrotate.conf.out /etc/logrotate.d/fledge

sudo chmod 644 /etc/rsyslog.d/fledge.conf /etc/logrotate.d/fledge
sudo chown -R root:root /etc/rsyslog.d/fledge.conf /etc/logrotate.d/fledge
sudo chown -R root:syslog ${FLEDGE_ROOT}/data/logs

sudo systemctl restart rsyslog.service


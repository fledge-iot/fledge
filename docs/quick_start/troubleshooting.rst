Troubleshooting Fledge
#######################

Fledge logs status and error messages to syslog.  To troubleshoot a Fledge installation using this information, open a session to the Fledge server and type::

  grep -a 'fledge' /var/log/syslog | tail -n 20

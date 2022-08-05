.. |br| raw:: html

   <br />

.. Links
.. _curl homepage: https://curl.haxx.se/
.. _curl sources: https://github.com/curl/curl/releases
.. _OMF: https://omf-docs.osisoft.com/

OMF Kerberos Authentication
***************************

Introduction
============

The bundled OMF north plugin in Fledge can use a number of different authentication schemes when communicating with the various OSIsoft products. The PI Web API method in the `OMF`_ plugin supports the use of a Kerberos scheme.

The Fledge *requirements.sh* script installs the Kerberos client to allow the integration with what in the specific terminology is called KDC (the Kerberos server).

PI Server as the North endpoint
===============================

The OSI *Connector Relay* allows token authentication while *PI Web API* supports Basic and Kerberos authentication.

There could be more than one configuration to allow the Kerberos authentication,
the easiest one is the Windows server on which the PI Server is executed act as the Kerberos server also.

The Windows Active directory should be installed and properly configured for allowing the Windows server to authenticate Kerberos requests.

North plugin
============

The North plugin has a set of configurable options that should be changed, using either the Fledge API or the Fledge GUI,
to select the Kerberos authentication.

The North plugin supports the configurable option *PIServerEndpoint* for allowing to select the target among:

  - Connector Relay

  - PI Web API

  - Edge Data Store

  - OSIsoft Cloud Services

The *PIWebAPIAuthenticationMethod* option permits to select the desired authentication among:

  - anonymous
  - basic
  - kerberos

The Kerberos authentication requires a keytab file, the *PIWebAPIKerberosKeytabFileName* option specifies the name of the file expected under the directory:

.. code-block:: console

  ${FLEDGE_ROOT}/data/etc/kerberos

**NOTE:**

- *A keytab is a file containing pairs of Kerberos principals and encrypted keys (which are derived from the Kerberos password). A keytab file allows to authenticate to various remote systems using Kerberos without entering a password.*

the *AFHierarchy1Level* option allows to specific the first level of the hierarchy that will be created into the Asset Framework and will contain the information for the specific
North plugin.


Fledge server configuration
============================
The server on which Fledge is going to be executed needs to be properly configured to allow the Kerberos authentication.

The following steps are needed:

  - *IP Address resolution for the KDC*

  - *Kerberos client configuration*

   - *Kerberos keytab file setup*

IP Address resolution of the KDC
--------------------------------
The Kerberos server name should be resolved to the corresponding IP Address, editing the */etc/hosts* is one of the possible and the easiest way, sample row to add:

.. code-block:: console

	192.168.1.51    pi-server.dianomic.com pi-server

try the resolution of the name using the usual *ping* command:

.. code-block:: console

	$ ping -c 1 pi-server.dianomic.com

	PING pi-server.dianomic.com (192.168.1.51) 56(84) bytes of data.
	64 bytes from pi-server.dianomic.com (192.168.1.51): icmp_seq=1 ttl=128 time=0.317 ms
	64 bytes from pi-server.dianomic.com (192.168.1.51): icmp_seq=2 ttl=128 time=0.360 ms
	64 bytes from pi-server.dianomic.com (192.168.1.51): icmp_seq=3 ttl=128 time=0.455 ms

**NOTE:**

- *the name of the KDC should be the first in the list of aliases*


Kerberos client configuration
-----------------------------
The server on which Fledge runs act like a Kerberos client and the related configuration file should be edited for allowing the proper Kerberos server identification.
The information should be added into the */etc/krb5.conf* file in the corresponding section, for example:

.. code-block:: console

	[libdefaults]
		default_realm = DIANOMIC.COM

	[realms]
	    DIANOMIC.COM = {
	        kdc = pi-server.dianomic.com
	        admin_server = pi-server.dianomic.com
	    }

Kerberos keytab file
--------------------
The keytab file should be generated on the Kerberos server and copied into the Fledge server in the directory:

.. code-block:: console

	${FLEDGE_DATA}/etc/kerberos

**NOTE:**

- if **FLEDGE_DATA** is not set its value should be *$FLEDGE_ROOT/data*.

The name of the file should match the value of the North plugin option *PIWebAPIKerberosKeytabFileName*, by default *piwebapi_kerberos_https.keytab*

.. code-block:: console

	$ ls -l ${FLEDGE_DATA}/etc/kerberos
	-rwxrwxrwx 1 fledge fledge  91 Jul 17 09:07 piwebapi_kerberos_https.keytab
	-rw-rw-r-- 1 fledge fledge 199 Aug 13 15:30 README.rst

The way the keytab file is generated depends on the type of the Kerberos server, in the case of Windows Active Directory this is an sample command:

.. code-block:: console

	ktpass -princ HTTPS/pi-server@DIANOMIC.COM -mapuser Administrator@DIANOMIC.COM -pass Password -crypto AES256-SHA1 -ptype KRB5_NT_PRINCIPAL -out C:\Temp\piwebapi_kerberos_https.keytab

Troubleshooting the Kerberos authentication
--------------------------------------------

1) check the North plugin configuration, a sample command

.. code-block:: console

    curl -s -S -X GET http://localhost:8081/fledge/category/North_Readings_to_PI | jq ".|{URL,"PIServerEndpoint",PIWebAPIAuthenticationMethod,PIWebAPIKerberosKeytabFileName,AFHierarchy1Level}"

2) check the presence of the keytab file

.. code-block:: console

	$ ls -l ${FLEDGE_ROOT}/data/etc/kerberos
	-rwxrwxrwx 1 fledge fledge  91 Jul 17 09:07 piwebapi_kerberos_https.keytab
	-rw-rw-r-- 1 fledge fledge 199 Aug 13 15:30 README.rst

3) verify the reachability of the Kerberos server (usually the PI Server) - Network reachability

.. code-block:: console

    $ ping pi-server.dianomic.com
    PING pi-server.dianomic.com (192.168.1.51) 56(84) bytes of data.
    64 bytes from pi-server.dianomic.com (192.168.1.51): icmp_seq=1 ttl=128 time=5.07 ms
    64 bytes from pi-server.dianomic.com (192.168.1.51): icmp_seq=2 ttl=128 time=1.92 ms

Kerberos reachability and keys retrieval

.. code-block:: console

    $ kinit -p HTTPS/pi-server@DIANOMIC.COM
    Password for HTTPS/pi-server@DIANOMIC.COM:
    $ klist
    Ticket cache: FILE:/tmp/krb5cc_1001
    Default principal: HTTPS/pi-server@DIANOMIC.COM

    Valid starting       Expires              Service principal
    09/27/2019 11:51:47  09/27/2019 21:51:47  krbtgt/DIANOMIC.COM@DIANOMIC.COM
        renew until 09/28/2019 11:51:46
    $

Kerberos authentication on RedHat/CentOS
========================================
RedHat and CentOS version 7 provide by default an old version of curl and the related libcurl
and it does not support Kerberos, output of the curl provided by CentOS:

.. code-block:: console

    $ curl -V
    curl 7.29.0 (x86_64-redhat-linux-gnu) libcurl/7.29.0 NSS/3.36 zlib/1.2.7 libidn/1.28 libssh2/1.4.3
    Protocols: dict file ftp ftps gopher http https imap imaps ldap ldaps pop3 pop3s rtsp scp sftp smtp smtps telnet tftp
    Features: AsynchDNS GSS-Negotiate IDN IPv6 Largefile NTLM NTLM_WB SSL libz unix-sockets

The *requirements.sh* evaluates if the default version 7.29.0 is installed and in this case it will download the sources, build and install
the version 7.65.3 to provide Kerberos authentication, output of the curl after the upgrade:

.. code-block:: console

    $ curl -V
    curl 7.65.3 (x86_64-unknown-linux-gnu) libcurl/7.65.3 OpenSSL/1.0.2k-fips zlib/1.2.7
    Release-Date: 2019-07-19
    Protocols: dict file ftp ftps gopher http https imap imaps pop3 pop3s rtsp smb smbs smtp smtps telnet tftp
    Features: AsynchDNS GSS-API HTTPS-proxy IPv6 Kerberos Largefile libz NTLM NTLM_WB SPNEGO SSL UnixSockets

The sources are downloaded from the curl repository `curl sources`_, the curl homepage is available at `curl homepage`_.

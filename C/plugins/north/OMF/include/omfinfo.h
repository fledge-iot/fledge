#ifndef _OMFINFO_H
#define _OMFINFO_H
/*
 * Fledge OSIsoft OMF interface to PI Server.
 *
 * Copyright (c) 2023 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string>
#include <logger.h>
#include <plugin_exception.h>
#include <iostream>
#include <omf.h>
#include <piwebapi.h>
#include <ocs.h>
#include <simple_https.h>
#include <simple_http.h>
#include <config_category.h>
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "json_utils.h"
#include "libcurl_https.h"
#include "utils.h"
#include "string_utils.h"
#include <version.h>
#include <linkedlookup.h>

#include "crypto.hpp"

#define PLUGIN_NAME "OMF"
#define TYPE_ID_KEY "type-id"
#define SENT_TYPES_KEY "sentDataTypes"
#define DATA_KEY "dataTypes"
#define DATA_KEY_SHORT "dataTypesShort"
#define DATA_KEY_HINT "hintChecksum"
#define NAMING_SCHEME "namingScheme"
#define AFH_HASH "afhHash"
#define AF_HIERARCHY "afHierarchy"
#define AF_HIERARCHY_ORIG "afHierarchyOrig"


#define PROPERTY_TYPE   "type"
#define PROPERTY_NUMBER "number"
#define PROPERTY_STRING "string"

#define ENDPOINT_URL_PI_WEB_API "https://HOST_PLACEHOLDER:PORT_PLACEHOLDER/piwebapi/omf"
#define ENDPOINT_URL_CR         "https://HOST_PLACEHOLDER:PORT_PLACEHOLDER/ingress/messages"
#define ENDPOINT_URL_OCS        "https://REGION_PLACEHOLDER.osisoft.com:PORT_PLACEHOLDER/api/v1/tenants/TENANT_ID_PLACEHOLDER/Namespaces/NAMESPACE_ID_PLACEHOLDER/omf"
#define ENDPOINT_URL_ADH        "https://REGION_PLACEHOLDER.datahub.connect.aveva.com:PORT_PLACEHOLDER/api/v1/Tenants/TENANT_ID_PLACEHOLDER/Namespaces/NAMESPACE_ID_PLACEHOLDER/omf"

#define ENDPOINT_URL_EDS        "http://localhost:PORT_PLACEHOLDER/api/v1/tenants/default/namespaces/default/omf"


enum OMF_ENDPOINT_PORT {
	ENDPOINT_PORT_PIWEB_API=443,
	ENDPOINT_PORT_CR=5460,
	ENDPOINT_PORT_OCS=443,
	ENDPOINT_PORT_EDS=5590,
	ENDPOINT_PORT_ADH=443
};

/**
 * Plugin specific default configuration
 */

#define NOT_BLOCKING_ERRORS_DEFAULT QUOTE(                              \
	{                                                                   \
		"errors400" : [                                                 \
			"Redefinition of the type with the same ID is not allowed", \
			"Invalid value type for the property",                      \
			"Property does not exist in the type definition",           \
			"Container is not defined",                                 \
			"Unable to find the property of the container of type"      \
		]			                                            \
	}                                                                   \
)

#define NOT_BLOCKING_ERRORS_DEFAULT_PI_WEB_API QUOTE(            \
	{                                                            \
		"EventInfo" : [                                          \
			"The specified value is outside the allowable range" \
		]			                                     \
	}                                                            \
)

#define AF_HIERARCHY_RULES QUOTE(                                          \
	{                                                                     \
	}                                                                     \
)

/**
 * A class that holds the configuration information for the OMF plugin.
 *
 * Note this is the first stage of refactoring the OMF plugins and represents
 * the CONNECTOR_INFO structure of original plugin as a class
 */
class OMFInformation {
	public:
		OMFInformation(ConfigCategory* configData);
		~OMFInformation();
		void		start(const std::string& storedData);
		uint32_t	send(const vector<Reading *>& readings);
		std::string	saveData();
	private:
		void 		loadSentDataTypes(rapidjson::Document& JSONData);
		long		getMaxTypeId();
		int		PIWebAPIGetVersion(bool logMessage = true);
		int		EDSGetVersion();
		void		SetOMFVersion();
		std::string	OCSRetrieveAuthToken();
		OMF_ENDPOINT	identifyPIServerEndpoint();
		std::string	saveSentDataTypes();
		unsigned long	calcTypeShort(const std::string& dataTypes);
		void		ParseProductVersion(std::string &versionString, int *major, int *minor);
		std::string	ParseEDSProductInformation(std::string json);
		std::string	AuthBasicCredentialsGenerate(std::string& userId, std::string& password);
		void		AuthKerberosSetup(std::string& keytabEnv, std::string& keytabFileName);
		double		GetElapsedTime(struct timeval *startTime);
		bool		IsPIWebAPIConnected();
		
	private:
		Logger		*m_logger;
		HttpSender	*m_sender;              // HTTPS connection
		OMF 		*m_omf;                 // OMF data protocol
		bool		m_sendFullStructure;    // It sends the minimum OMF structural messages to load data into PI Data Archive if disabled
		bool		m_compression;          // whether to compress readings' data
		string		m_protocol;             // http / https
		string		m_hostAndPort;          // hostname:port for SimpleHttps
		unsigned int	m_retrySleepTime;     	// Seconds between each retry
		unsigned int	m_maxRetry;	        // Max number of retries in the communication
		unsigned int	m_timeout;	        // connect and operation timeout
		string		m_path;		        // PI Server application path
		string		m_delimiter;			// delimiter between Asset and Datapoint in PI data stream names
		long		m_typeId;		        // OMF protocol type-id prefix
		string		m_producerToken;	        // PI Server connector token
		string		m_formatNumber;	        // OMF protocol Number format
		string		m_formatInteger;	        // OMF protocol Integer format
		OMF_ENDPOINT	m_PIServerEndpoint;     // Defines which End point should be used for the communication
		NAMINGSCHEME_ENDPOINT
				m_NamingScheme; // Define how the object names should be generated - https://fledge-iot.readthedocs.io/en/latest/OMF.html#naming-scheme
		string		m_DefaultAFLocation;    // 1st hierarchy in Asset Framework, PI Web API only.
		string		m_AFMap;                // Defines a set of rules to address where assets should be placed in the AF hierarchy.
						//    https://fledge-iot.readthedocs.io/en/latest/OMF.html#asset-framework-hierarchy-rules

		string		m_prefixAFAsset;        // Prefix to generate unique asset id
		string		m_PIWebAPIProductTitle;
		string		m_RestServerVersion;
		string		m_PIWebAPIAuthMethod;   // Authentication method to be used with the PI Web API.
		string		m_PIWebAPICredentials;  // Credentials is the base64 encoding of id and password joined by a single colon (:)
		string 		m_KerberosKeytab;       // Kerberos authentication keytab file
						    //   stores the environment variable value about the keytab file path
						    //   to allow the environment to persist for all the execution of the plugin
						    //
						    //   Note : A keytab is a file containing pairs of Kerberos principals
						    //   and encrypted keys (which are derived from the Kerberos password).
						    //   You can use a keytab file to authenticate to various remote systems
						    //   using Kerberos without entering a password.

		string		m_OCSNamespace;           // OCS configurations
		string		m_OCSTenantId;
		string		m_OCSClientId;
		string		m_OCSClientSecret;
		string		m_OCSToken;

		vector<pair<string, string>>
				m_staticData;	// Static data
		// Errors considered not blocking in the communication with the PI Server
		std::vector<std::string>
				m_notBlockingErrors;
		// Per asset DataTypes
		std::map<std::string, OMFDataTypes>
				m_assetsDataTypes;
		string		m_omfversion;
		bool		m_legacy;
		string		m_name;
		bool		m_connected;
};
#endif

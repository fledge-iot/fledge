/*
 * Fledge OSIsoft OMF interface to PI Server.
 *
 * Copyright (c) 2023-2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <omfinfo.h>
#include <utils.h>

using namespace std;
using namespace rapidjson;
using namespace SimpleWeb;

/**
 * Constructor for the OMFInformation class
 */
OMFInformation::OMFInformation(ConfigCategory *config) : m_sender(NULL), m_omf(NULL), m_ocs(NULL), m_connected(false)
{

	m_logger = Logger::getLogger();
	m_name = config->getName();
	m_numBlocks = 1;

	int endpointPort = 0;

	// PIServerEndpoint handling
	string PIServerEndpoint = config->getValue("PIServerEndpoint");
	string ADHRegions = config->getValue("ADHRegions");
	string ServerHostname = config->getValue("ServerHostname");
	if (gethostbyname(ServerHostname.c_str()) == NULL)
	{
		Logger::getLogger()->warn("Unable to resolve server hostname '%s'. This should be a valid hostname or IP Address.", ServerHostname.c_str());
	}
	string ServerPort = config->getValue("ServerPort");
	string url;
	string NamingScheme = config->getValue("NamingScheme");

	// Translate the PIServerEndpoint configuration
	if(PIServerEndpoint.compare("PI Web API") == 0)
	{
		Logger::getLogger()->debug("PI-Server end point manually selected - PI Web API ");
		m_PIServerEndpoint = ENDPOINT_PIWEB_API;
		url                        = ENDPOINT_URL_PI_WEB_API;
		endpointPort               = ENDPOINT_PORT_PIWEB_API;
	}
	else if(PIServerEndpoint.compare("Connector Relay") == 0)
	{
		Logger::getLogger()->debug("PI-Server end point manually selected - Connector Relay ");
		m_PIServerEndpoint = ENDPOINT_CR;
		url                = ENDPOINT_URL_CR;
		endpointPort       = ENDPOINT_PORT_CR;
	}
	else if(PIServerEndpoint.compare("AVEVA Data Hub") == 0)
	{
		Logger::getLogger()->debug("End point manually selected - AVEVA Data Hub");
		m_PIServerEndpoint = ENDPOINT_ADH;
		url 		   = ENDPOINT_URL_ADH;
		std::string region = "uswe";
		if(ADHRegions.compare("EU-West") == 0)
			region = "euno";
		else if(ADHRegions.compare("Australia") == 0)
			region = "auea";
		StringReplace(url, "REGION_PLACEHOLDER", region);
		endpointPort       = ENDPOINT_PORT_ADH;
	}
	else if(PIServerEndpoint.compare("OSIsoft Cloud Services") == 0)
	{
		Logger::getLogger()->debug("End point manually selected - OSIsoft Cloud Services");
		m_PIServerEndpoint = ENDPOINT_OCS;
		url                = ENDPOINT_URL_OCS;
		std::string region = "dat-b";
		if(ADHRegions.compare("EU-West") == 0)
			region = "dat-d";
		else if(ADHRegions.compare("Australia") == 0)
			Logger::getLogger()->error("OSIsoft Cloud Services are not hosted in Australia");
		StringReplace(url, "REGION_PLACEHOLDER", region);
		endpointPort       = ENDPOINT_PORT_OCS;
	}
	else if(PIServerEndpoint.compare("Edge Data Store") == 0)
	{
		Logger::getLogger()->debug("End point manually selected - Edge Data Store");
		m_PIServerEndpoint = ENDPOINT_EDS;
		url                = ENDPOINT_URL_EDS;
		endpointPort       = ENDPOINT_PORT_EDS;
	}
	ServerPort = (ServerPort.compare("0") == 0) ? to_string(endpointPort) : ServerPort;

	if (endpointPort == ENDPOINT_PORT_PIWEB_API) 
    {
		// Use SendFullStructure ?
		m_sendFullStructure = stringToBool(config->getValue("SendFullStructure"));

	} else 
    {
		m_sendFullStructure = true;
	}

    m_tracingEnabled = stringToBool(config->getValue("EnableTracing"));

	unsigned int retrySleepTime = atoi(config->getValue("OMFRetrySleepTime").c_str());
	unsigned int maxRetry = atoi(config->getValue("OMFMaxRetry").c_str());
	unsigned int timeout = atoi(config->getValue("OMFHttpTimeout").c_str());

	string producerToken = config->getValue("producerToken");

	string formatNumber = config->getValue("formatNumber");
	string formatInteger = config->getValue("formatInteger");
	string DefaultAFLocation = config->getValue("DefaultAFLocation");
	string AFMap = config->getValue("AFMap");

	string PIWebAPIAuthMethod     = config->getValue("PIWebAPIAuthenticationMethod");
	string PIWebAPIUserId         = config->getValue("PIWebAPIUserId");
	string PIWebAPIPassword       = config->getValue("PIWebAPIPassword");
	string KerberosKeytabFileName = config->getValue("PIWebAPIKerberosKeytabFileName");

	// OCS configurations
	string OCSNamespace    = config->getValue("OCSNamespace");
	string OCSTenantId     = config->getValue("OCSTenantId");
	string OCSClientId     = config->getValue("OCSClientId");
	string OCSClientSecret = config->getValue("OCSClientSecret");

	StringReplace(url, "HOST_PLACEHOLDER", ServerHostname);
	StringReplace(url, "PORT_PLACEHOLDER", ServerPort);

	// TENANT_ID_PLACEHOLDER and NAMESPACE_ID_PLACEHOLDER, if present, will be replaced with the values of OCSTenantId and OCSNamespace
	StringReplace(url, "TENANT_ID_PLACEHOLDER",    OCSTenantId);
	StringReplace(url, "NAMESPACE_ID_PLACEHOLDER", OCSNamespace);

	/**
	 * Extract host, port, path from URL
	 */
	size_t findProtocol = url.find_first_of(":");
	string protocol = url.substr(0, findProtocol);

	string tmpUrl = url.substr(findProtocol + 3);
	size_t findPort = tmpUrl.find_first_of(":");
	string hostName = tmpUrl.substr(0, findPort);

	size_t findPath = tmpUrl.find_first_of("/");
	string port = tmpUrl.substr(findPort + 1, findPath - findPort - 1);
	string path = tmpUrl.substr(findPath);

	string hostAndPort(hostName + ":" + port);

	// Set configuration fields
	m_protocol = protocol;
	m_hostAndPort = hostAndPort;
	m_path = path;
	m_retrySleepTime = retrySleepTime;
	m_maxRetry = maxRetry;
	m_timeout = timeout;
	m_typeId = TYPE_ID_DEFAULT;
	m_producerToken = producerToken;
	m_formatNumber = formatNumber;
	m_formatInteger = formatInteger;
	m_DefaultAFLocation = DefaultAFLocation;
	m_AFMap = AFMap;

	// OCS configurations
	m_OCSNamespace    = OCSNamespace;
	m_OCSTenantId     = OCSTenantId;
	m_OCSClientId     = OCSClientId;
	m_OCSClientSecret = OCSClientSecret;

	// PI Web API end-point - evaluates the authentication method requested
	if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		if (PIWebAPIAuthMethod.compare("anonymous") == 0)
		{
			Logger::getLogger()->debug("PI Web API end-point - anonymous authentication");
			m_PIWebAPIAuthMethod = "a";
		}
		else if (PIWebAPIAuthMethod.compare("basic") == 0)
		{
			Logger::getLogger()->debug("PI Web API end-point - basic authentication");
			m_PIWebAPIAuthMethod = "b";
			m_PIWebAPICredentials = AuthBasicCredentialsGenerate(PIWebAPIUserId, PIWebAPIPassword);
		}
		else if (PIWebAPIAuthMethod.compare("kerberos") == 0)
		{
			Logger::getLogger()->debug("PI Web API end-point - kerberos authentication");
			m_PIWebAPIAuthMethod = "k";
			AuthKerberosSetup(m_KerberosKeytab, KerberosKeytabFileName);
		}
		else
		{
			Logger::getLogger()->error("Invalid authentication method for PI Web API :%s: ", PIWebAPIAuthMethod.c_str());
		}
	}
	else
	{
		// For all other endpoint types, set PI Web API authentication to 'anonymous.'
		// This prevents the HttpSender from inserting PI Web API authentication headers.
		m_PIWebAPIAuthMethod = "a";
	}

	// Use compression ?
	string compr = config->getValue("compression");
	if (compr == "True" || compr == "true" || compr == "TRUE")
		m_compression = true;
	else
		m_compression = false;

	// Set the list of errors considered not blocking in the communication
	// with the PI Server
	if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		JSONStringToVectorString(m_notBlockingErrors,
					 config->getValue("PIWebAPInotBlockingErrors"),
					 string("EventInfo"));
	}
	else
	{
		JSONStringToVectorString(m_notBlockingErrors,
					 config->getValue("notBlockingErrors"),
					 string("errors400"));
	}
	/**
	 * Add static data
	 * Split the string up into each pair
	 */
	string staticData = config->getValue("StaticData");
	size_t pos = 0;
	size_t start = 0;
	do {
		pos = staticData.find(",", start);
		string item = staticData.substr(start, pos - start);
		start = pos + 1;
		size_t pos2 = 0;
		if ((pos2 = item.find(":")) != string::npos)
		{
			string name = item.substr(0, pos2);
			while (name[0] == ' ')
				name = name.substr(1);
			string value = item.substr(pos2 + 1);
			while (value[0] == ' ')
				value = value.substr(1);
			if (!name.empty() && !value.empty())
			{
				pair<string, string> sData = make_pair(name, value);
				m_staticData.push_back(sData);
			}
		}
	} while (pos != string::npos);

	// Set Asset/Datapoint data stream name delimiter
	m_delimiter = config->getValue("AssetDatapointNameDelimiter");
	if (m_delimiter.empty())
	{
		// Delimiter can't be empty. If the user has cleared it, set it to the default.
		m_delimiter = ".";
	}
	else
	{
		StringTrim(m_delimiter);
		if (m_delimiter.empty())
		{
			// If trimming emptied the string, the delimiter is a blank which is legal
			m_delimiter = " ";
		}
		else
		{
			// Delimiter must be a single character
			m_delimiter.resize(1);
		}
	}

	// Set the Action Code for OMF Data posts: update or create
	m_dataActionCode = config->itemExists("OMFDataActionCode") ? config->getValue("OMFDataActionCode") : "update";

	{
		// NamingScheme handling
		if(NamingScheme.compare("Concise") == 0)
		{
			m_NamingScheme = NAMINGSCHEME_CONCISE;
		}
		else if(NamingScheme.compare("Use Type Suffix") == 0)
		{
			m_NamingScheme = NAMINGSCHEME_SUFFIX;
		}
		else if(NamingScheme.compare("Use Attribute Hash") == 0)
		{
			m_NamingScheme = NAMINGSCHEME_HASH;
		}
		else if(NamingScheme.compare("Backward compatibility") == 0)
		{
			m_NamingScheme = NAMINGSCHEME_COMPATIBILITY;
		}
		Logger::getLogger()->debug("End point naming scheme :%s: ", NamingScheme.c_str() );

	}

	// Fetch legacy OMF type option
	string legacy = config->getValue("Legacy");
	if (legacy == "True" || legacy == "true" || legacy == "TRUE")
		m_legacy = true;
	else
		m_legacy = false;
    
    // Enable or disable OMF tracing based on the current configuration
    handleOMFTracing();
}

/**
 * @brief Handles the enabling and configuration of OMF tracing.
 *
 * If OMF tracing is enabled, this function checks if the trace file exists.
 * If it does not exist, the file is created in write mode. If the file
 * exists but is read-only, the function changes the file permissions to
 * allow writing. If OMF tracing is disabled, it checks if the trace file
 * exists and has write permissions, and if so, sets it to read-only.
 */
void OMFInformation::handleOMFTracing() 
{
    std::string filename = HttpSender::getOMFTracePath(); // Retrieve the trace file path

    if (m_tracingEnabled) 
    {
        if(!HttpSender::createDebugTraceDirectory())
        {
            return;
        }

        // Check if the trace file exists
        std::ifstream fileCheck(filename.c_str());
        if (!fileCheck) 
        {
            // File does not exist, create it in write mode
            std::ofstream traceFile(filename.c_str(), std::ofstream::out);
            if (!traceFile) 
            {
                Logger::getLogger()->error("Unable to create trace file: %s", filename.c_str());
            } 
        } 
        else 
        {
            // File exists, check if it is read-only
            struct stat fileStat;
            if (stat(filename.c_str(), &fileStat) == 0) 
            {
                // Check if the file is read-only
                if (!(fileStat.st_mode & S_IWUSR)) 
                {
                    // Change the file permissions to allow writing
                    if (chmod(filename.c_str(), fileStat.st_mode | S_IWUSR) != 0) 
                    {
                        Logger::getLogger()->error("Unable to set write permissions for: %s", filename.c_str());
                    } 
                }
            }
        }
    } 
    else 
    {
        // Check if the trace file exists before attempting to make it read-only
        if (access(filename.c_str(), F_OK) == 0) 
        {
            // Check if the file has write permissions
            struct stat fileStat;
            if (stat(filename.c_str(), &fileStat) == 0) 
            {
                // If the file has write permission, change it to read-only
                if (fileStat.st_mode & S_IWUSR) 
                {
                    if (chmod(filename.c_str(), fileStat.st_mode & ~S_IWUSR) != 0) 
                    {
                        Logger::getLogger()->error("Unable to set read-only permissions for: %s", filename.c_str());
                    } 
                }
            }
        } 
    }
}

/**
 * Destructor for the OMFInformation class.
 */
OMFInformation::~OMFInformation()
{
	delete m_sender;
	delete m_omf;
	delete m_ocs;
	// TODO cleanup the allocated member variables
}

/**
 * The plugin start entry point has been called
 *
 * @param storedData	The data that has been persisted by a previous execution
 * of the plugin
 */
void OMFInformation::start(const string& storedData)
{
	m_logger->info("Host: %s", m_hostAndPort.c_str());
	if ((m_PIServerEndpoint == ENDPOINT_OCS) || (m_PIServerEndpoint == ENDPOINT_ADH))
	{
		m_logger->info("Namespace: %s", m_OCSNamespace.c_str());
	}

	// Parse JSON plugin_data
	Document JSONData;
	JSONData.Parse(storedData.c_str());
	if (JSONData.HasParseError())
	{
		m_logger->error("%s plugin error: failure parsing "
			      "plugin data JSON object '%s'",
			      PLUGIN_NAME,
			      storedData.c_str());
	}
	else if (JSONData.HasMember(TYPE_ID_KEY) &&
		(JSONData[TYPE_ID_KEY].IsString() ||
		 JSONData[TYPE_ID_KEY].IsNumber()))
	{
		// Update type-id in PLUGIN_HANDLE object
		if (JSONData[TYPE_ID_KEY].IsNumber())
		{
			m_typeId = JSONData[TYPE_ID_KEY].GetInt();
		}
		else
		{
			m_typeId = atol(JSONData[TYPE_ID_KEY].GetString());
		}
	}

	// Check if the configured Asset/Datapoint delimiter is legal in OMF which uses PI and AF rules
	bool changed = false;
	OMF::ApplyPIServerNamingRulesInvalidChars(m_delimiter, &changed);
	if (changed)
	{
		m_logger->error("Asset/Datapoint name delimiter '%s' is not legal in OMF", m_delimiter.c_str());
	}
	else
	{
		m_logger->info("Asset/Datapoint name delimiter set to '%s'", m_delimiter.c_str());
	}

	// Load sentdataTypes
	loadSentDataTypes(JSONData);

	// Log default type-id
	if (m_assetsDataTypes.size() == 1 &&
	    m_assetsDataTypes.find(FAKE_ASSET_KEY) != m_assetsDataTypes.end())
	{
		// Only one value: we have the FAKE_ASSET_KEY and no other data
		Logger::getLogger()->info("%s plugin is using global OMF prefix %s=%d",
					  PLUGIN_NAME,
					  TYPE_ID_KEY,
					  m_typeId);
	}
	else
	{
		Logger::getLogger()->info("%s plugin is using per asset OMF prefix %s=%d "
					  "(max value found)",
					  PLUGIN_NAME,
					  TYPE_ID_KEY,
					  getMaxTypeId());
	}

	// Allocate an HttpSender subclass to communicate with PI Web API with selected authorization
	if (!m_sender)
	{
		/**
		 * Select the transport library based on the authentication method and transport encryption
		 * requirements.
		 *
		 * LibcurlHttps is used to integrate Kerberos as the SimpleHttp does not support it
		 * the Libcurl integration implements only HTTPS not HTTP currently. We use SimpleHttp or
		 * SimpleHttps, as appropriate for the URL given, if not using Kerberos
		 *
		 *
		 * The handler is allocated using "Hostname : port", connect_timeout and request_timeout.
		 * Default is no timeout
		 */
		if (m_PIWebAPIAuthMethod.compare("k") == 0)
		{
			m_sender = new LibcurlHttps(m_hostAndPort,
							    m_timeout,
							    m_timeout,
							    m_retrySleepTime,
							    m_maxRetry);
		}
		else
		{
			if (m_protocol.compare("http") == 0)
			{
				m_sender = new SimpleHttp(m_hostAndPort,
								  m_timeout,
								  m_timeout,
								  m_retrySleepTime,
								  m_maxRetry);
			}
			else
			{
				m_sender = new SimpleHttps(m_hostAndPort,
								   m_timeout,
								   m_timeout,
								   m_retrySleepTime,
								   m_maxRetry);
			}
		}

		m_sender->setAuthMethod          (m_PIWebAPIAuthMethod);
		m_sender->setAuthBasicCredentials(m_PIWebAPICredentials);

		// OCS configurations
		m_sender->setOCSNamespace        (m_OCSNamespace);
		m_sender->setOCSTenantId         (m_OCSTenantId);
		m_sender->setOCSClientId         (m_OCSClientId);
		m_sender->setOCSClientSecret     (m_OCSClientSecret);
	}

	// Retrieve the destination data archive version
	m_connected = true;
	int httpCode = 200;
	switch (m_PIServerEndpoint)
	{
	case ENDPOINT_PIWEB_API:
		httpCode = PIWebAPIGetVersion();
		if (httpCode >= 200 && httpCode < 400)
		{
			SetOMFVersion();
			CheckDataActionCode();
			Logger::getLogger()->info("%s connected to %s OMF Version: %s",
									  m_RestServerVersion.c_str(), m_hostAndPort.c_str(), m_omfversion.c_str());
			m_connected = true;
		}
		else
		{
			Logger::getLogger()->error("The PI Web API service %s is not available. HTTP Code: %d",
									   m_hostAndPort.c_str(), httpCode);
			m_connected = false;
		}
		break;
	case ENDPOINT_EDS:
		httpCode = EDSGetVersion();
		if (httpCode >= 200 && httpCode < 400)
		{
			SetOMFVersion();
			CheckDataActionCode();
			Logger::getLogger()->info("Edge Data Store %s OMF Version: %s", m_RestServerVersion.c_str(), m_omfversion.c_str());
			m_connected = true;
		}
		else
		{
			Logger::getLogger()->error("Edge Data Store %s is not available. HTTP Code: %d",
									   m_hostAndPort.c_str(), httpCode);
			m_connected = false;
		}
		break;
	case ENDPOINT_OCS:
		SetOMFVersion();
		CheckDataActionCode();
		Logger::getLogger()->info("OSIsoft Cloud Services OMF Version: %s", m_omfversion.c_str());
		break;
	case ENDPOINT_ADH:
		SetOMFVersion();
		CheckDataActionCode();
		Logger::getLogger()->info("AVEVA Data Hub OMF Version: %s", m_omfversion.c_str());
		break;
	case ENDPOINT_CR:
		SetOMFVersion();
		CheckDataActionCode();
		Logger::getLogger()->info("Connector Relay OMF Version: %s", m_omfversion.c_str());
		break;
	default:
		SetOMFVersion();
		CheckDataActionCode();
		Logger::getLogger()->info("OMF Version: %s", m_omfversion.c_str());
		break;
	}

	// Allocate the OMF class that implements the PI Server data protocol
	if (!m_omf)
	{
		m_omf = new OMF(m_name, *m_sender, m_path, m_assetsDataTypes,
				m_producerToken);

		m_omf->setSendFullStructure(m_sendFullStructure);
		m_omf->setDelimiter(m_delimiter);

		// Set PIServerEndpoint configuration
		m_omf->setNamingScheme(m_NamingScheme);
		m_omf->setPIServerEndpoint(m_PIServerEndpoint);
		m_omf->setDefaultAFLocation(m_DefaultAFLocation);
		m_omf->setAFMap(m_AFMap);

		// Generates the prefix to have unique asset_id across different levels of hierarchies
		string AFHierarchyLevel;
		m_omf->generateAFHierarchyPrefixLevel(m_DefaultAFLocation, m_prefixAFAsset, AFHierarchyLevel);

		m_omf->setPrefixAFAsset(m_prefixAFAsset);

		// Set OMF FormatTypes  
		m_omf->setFormatType(OMF_TYPE_FLOAT,
					     m_formatNumber);
		m_omf->setFormatType(OMF_TYPE_INTEGER,
					     m_formatInteger);

		m_omf->setStaticData(&m_staticData);
		m_omf->setNotBlockingErrors(m_notBlockingErrors);

		if (m_omfversion == "1.1" || m_omfversion == "1.0")
		{
			Logger::getLogger()->info("Setting LegacyType to be true for OMF Version '%s'. This will force use old style complex types. ", m_omfversion.c_str());
			m_omf->setLegacyMode(true);
		}
		else
		{
			m_omf->setLegacyMode(m_legacy);
		}
	}

	// Allocate the OCS class that implements ADH and OCS authentication
	if (!m_ocs)
	{
		if (m_PIServerEndpoint == ENDPOINT_ADH)
		{
			m_ocs = new OCS(true);
		}
		else if (m_PIServerEndpoint == ENDPOINT_OCS)
		{
			m_ocs = new OCS(false);
		}
	}
}

/**
 * Send data to the OMF endpoint
 *
 * @param readings	The block of readings to send
 * @return uint32_t	The number of readings sent
 */
uint32_t OMFInformation::send(const vector<Reading *>& readings)
{
#if INSTRUMENT
	struct timeval startTime;
	gettimeofday(&startTime, NULL);
#endif
	// Check if the destination data archive is available
	if (!IsDataArchiveConnected())
	{
		// Error already reported by IsDataArchiveConnected
		return 0;
	}

	// For OCS and ADH, retrieve the authentication token
	if (m_ocs)
	{
		std::string token = m_ocs->OCSRetrieveAuthToken(m_OCSClientId, m_OCSClientSecret);
		if (!token.empty())
		{
			m_OCSToken = token;
			m_sender->setOCSToken(token);
		}
	}

	// Exit immediately if the plugin is not stable due to PI Server errors
	if (!m_omf->isPIstable())
	{
		return 0;
	}

	// Send the readings data to the PI Server
	m_omf->setOMFVersion(m_omfversion);
	m_omf->setDataActionCode(m_dataActionCode);
	m_omf->setPIconnected(m_connected);
	m_omf->setNumBlocks(m_numBlocks);

	uint32_t ret = m_omf->sendToServer(readings, m_compression);

	m_connected = m_omf->isPIconnected();
	m_numBlocks = m_omf->getNumBlocks();

	// Detect typeId change in OMF class
	if (m_omf->getTypeId() != m_typeId)
	{
		// Update typeId in plugin handle
		m_typeId = m_omf->getTypeId();
		// Log change
		Logger::getLogger()->info("%s plugin: a new OMF global %s (%d) has been created.",
					  PLUGIN_NAME,
					  TYPE_ID_KEY,
					  m_typeId);
	}
	
#if INSTRUMENT
	Logger::getLogger()->debug("plugin_send elapsed time: %6.3f seconds, NumValues: %u", GetElapsedTime(&startTime), ret);
#endif

	// Return sent data ret code
	return ret;
}

/**
 * Return the data to be persisted
 * @return string	The data to persist
 */
string OMFInformation::saveData()
{
#if INSTRUMENT
	struct timeval startTime;
	gettimeofday(&startTime, NULL);
#endif
	// Create save data
	std::ostringstream saveData;
	saveData << "{";

	// Add sent data types
	string typesData = saveSentDataTypes();
	if (!typesData.empty())
	{
		// Save datatypes
		saveData << typesData;
	}
	else
	{
		// Just save type-id
		saveData << "\"" << TYPE_ID_KEY << "\": " << to_string(m_typeId);
	}

	saveData << "}";

        // Log saving the plugin configuration
        Logger::getLogger()->debug("%s plugin: saving plugin_data '%s'",
				   PLUGIN_NAME,
				   saveData.str().c_str());


#if INSTRUMENT
	// For debugging: write plugin's JSON data to a file
	string jsonFilePath = getDataDir() + string("/logs/OMFSaveData.json");
	ofstream f(jsonFilePath.c_str(), ios_base::trunc);
	f << saveData.str();
	f.close();

	Logger::getLogger()->debug("plugin_shutdown elapsed time: %6.3f seconds", GetElapsedTime(&startTime));	
#endif

	// Return current plugin data to save
	return saveData.str();
}


/**
 * Load stored data types (already sent to PI server)
 *
 * Each element, the assetName, has type-id and datatype for each datapoint
 *
 * If no data exists in the plugin_data table, then a map entry
 * with FAKE_ASSET_KEY is made in order to set the start type-id
 * sequence with default value set to 1:
 * all new created OMF dataTypes have type-id prefix set to the value of 1.
 *
 * If data like {"type-id": 14} or {"type-id": "14" } is found, a map entry
 * with FAKE_ASSET_KEY is made and the start type-id sequence value is set
 * to the found value, i.e. 14:
 * all new created OMF dataTypes have type-id prefix set to the value of 14.
 *
 * If proper per asset types data is loaded, the FAKE_ASSET_KEY is not set:
 * all new created OMF dataTypes have type-id prefix set to the value of 1
 * while existing (loaded) OMF dataTypes will keep their type-id values.
 *
 * @param   JSONData	The JSON document containing all saved data
 */
void OMFInformation::loadSentDataTypes(Document& JSONData)
{
	if (JSONData.HasMember(SENT_TYPES_KEY) &&
	    JSONData[SENT_TYPES_KEY].IsArray())
	{
		const Value& cachedTypes = JSONData[SENT_TYPES_KEY];
		for (Value::ConstValueIterator it = cachedTypes.Begin();
						it != cachedTypes.End();
						++it)
		{
			if (!it->IsObject())
			{
				Logger::getLogger()->warn("%s plugin: current element in '%s' " \
							  "property is not an object, ignoring it",
							  PLUGIN_NAME,
							  SENT_TYPES_KEY);
				continue;
			}

			for (Value::ConstMemberIterator itr = it->MemberBegin();
							itr != it->MemberEnd();
							++itr)
			{
				string key = itr->name.GetString();
				const Value& cachedValue = itr->value;

				// Add typeId and dataTypes to the in memory cache
				long typeId;
				if (cachedValue.HasMember(TYPE_ID_KEY) &&
				    cachedValue[TYPE_ID_KEY].IsNumber())
				{
					typeId = cachedValue[TYPE_ID_KEY].GetInt();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property, ignoring it",
								  PLUGIN_NAME,
								  key.c_str(),
								  TYPE_ID_KEY);
					continue;
				}

				long NamingScheme;
				if (cachedValue.HasMember(NAMING_SCHEME) &&
					cachedValue[NAMING_SCHEME].IsNumber())
				{
					NamingScheme = cachedValue[NAMING_SCHEME].GetInt();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property, handling naming scheme in compatibility mode",
											  PLUGIN_NAME,
											  key.c_str(),
											  NAMING_SCHEME);
					NamingScheme = NAMINGSCHEME_COMPATIBILITY;
				}

				string AFHHash;
				if (cachedValue.HasMember(AFH_HASH) &&
					cachedValue[AFH_HASH].IsString())
				{
					AFHHash = cachedValue[AFH_HASH].GetString();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property",
											  PLUGIN_NAME,
											  key.c_str(),
											  AFH_HASH);
					AFHHash = "";
				}

				string AFHierarchy;
				if (cachedValue.HasMember(AF_HIERARCHY) &&
					cachedValue[AF_HIERARCHY].IsString())
				{
					AFHierarchy = cachedValue[AF_HIERARCHY].GetString();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property",
											  PLUGIN_NAME,
											  key.c_str(),
											  AF_HIERARCHY);
					AFHierarchy = "";
				}

				string AFHierarchyOrig;
				if (cachedValue.HasMember(AF_HIERARCHY_ORIG) &&
					cachedValue[AF_HIERARCHY_ORIG].IsString())
				{
					AFHierarchyOrig = cachedValue[AF_HIERARCHY_ORIG].GetString();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property",
											  PLUGIN_NAME,
											  key.c_str(),
											  AF_HIERARCHY_ORIG);
					AFHierarchyOrig = "";
				}

				string dataTypes;
				if (cachedValue.HasMember(DATA_KEY) &&
				    cachedValue[DATA_KEY].IsObject())
				{
					StringBuffer buffer;
					Writer<StringBuffer> writer(buffer);
					const Value& types = cachedValue[DATA_KEY];
					types.Accept(writer);
					dataTypes = buffer.GetString();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property, ignoring it",
								  PLUGIN_NAME,
								  key.c_str(),
								  DATA_KEY);

					continue;
				}

				unsigned long dataTypesShort;
				if (cachedValue.HasMember(DATA_KEY_SHORT) &&
					cachedValue[DATA_KEY_SHORT].IsString())
				{
					string strDataTypesShort = cachedValue[DATA_KEY_SHORT].GetString();
					// The information are stored as string in hexadecimal format
					dataTypesShort = stoi (strDataTypesShort,nullptr,16);
				}
				else
				{
					dataTypesShort = calcTypeShort(dataTypes);
					if (dataTypesShort == 0)
					{
						Logger::getLogger()->warn("%s plugin: current element '%s'" \
                                      " doesn't have '%s' property",
												  PLUGIN_NAME,
												  key.c_str(),
												  DATA_KEY_SHORT);
					}
					else
					{
						Logger::getLogger()->warn("%s plugin: current element '%s'" \
                                      " doesn't have '%s' property, calculated '0x%X'",
												  PLUGIN_NAME,
												  key.c_str(),
												  DATA_KEY_SHORT,
												  dataTypesShort);
					}
				}
				unsigned short hintChecksum = 0;
				if (cachedValue.HasMember(DATA_KEY_HINT) &&
					cachedValue[DATA_KEY_HINT].IsString())
				{
					string strHint = cachedValue[DATA_KEY_HINT].GetString();
					// The information are stored as string in hexadecimal format
					hintChecksum = stoi (strHint,nullptr,16);
				}
				OMFDataTypes dataType;
				dataType.typeId = typeId;
				dataType.types = dataTypes;
				dataType.typesShort = dataTypesShort;
				dataType.hintChkSum = hintChecksum;
				dataType.namingScheme = NamingScheme;
				dataType.afhHash = AFHHash;
				dataType.afHierarchy = AFHierarchy;
				dataType.afHierarchyOrig = AFHierarchyOrig;

				Logger::getLogger()->debug("%s - AFHHash :%s: AFHierarchy :%s: AFHierarchyOrig :%s: ", __FUNCTION__, AFHHash.c_str(), AFHierarchy.c_str() , AFHierarchyOrig.c_str() );


				Logger::getLogger()->debug("%s - NamingScheme :%ld: ", __FUNCTION__,NamingScheme );

				// Add data into the map
				m_assetsDataTypes[key] = dataType;
			}
		}
	}
	else
	{
		// There is no stored data when plugin starts first time 
		if (JSONData.MemberBegin() != JSONData.MemberEnd())
		{
			Logger::getLogger()->warn("Persisted data is not of the correct format, ignoring");
		}
		
		OMFDataTypes dataType;
		dataType.typeId = m_typeId;
		dataType.types = "{}";

		// Add default data into the map
		m_assetsDataTypes[FAKE_ASSET_KEY] = dataType;
	}
}



/**
 * Return the maximum value of type-id, among all entries in the map
 *
 * If the array is empty the m_typeId is returned.
 *
 * @return		The maximum value of type-id found
 */
long OMFInformation::getMaxTypeId()
{
	long maxId = m_typeId;
	for (auto it = m_assetsDataTypes.begin();
		  it != m_assetsDataTypes.end();
		  ++it)
	{
		if ((*it).second.typeId > maxId)
		{
			maxId = (*it).second.typeId;
		}
	}
	return maxId;
}

/**
 * Calls the PI Web API system information endpoint to get the product version
 * 
 * @param    logMessage	If true, log error messages (default: true)
 * @return   HttpCode	REST response code
 */
int OMFInformation::PIWebAPIGetVersion(bool logMessage)
{
	int res = 400;
	unsigned int retries = m_sender->getMaxRetries();
	m_sender->setMaxRetries(0);

	try
	{
		string path = "https://" + m_hostAndPort + "/piwebapi/system";

		vector<pair<string, string>> headers;
		headers.push_back( std::make_pair("Accept", "application/json"));

		m_RestServerVersion.clear();

		res = m_sender->sendRequest("GET", path, headers, std::string(""));
		if (res >= 200 && res <= 299)
		{
			PIWebAPI piwebapi;
			m_RestServerVersion = piwebapi.ExtractVersion(m_sender->getHTTPResponse());
		}
	}
	catch (const BadRequest &ex)
	{
		if (logMessage)
		{
			Logger::getLogger()->error("PI Web API system information BadRequest exception: %s", ex.what());
		}
		res = 400;
	}
	catch (const Unauthorized &e)
	{
		if (logMessage)
		{
			Logger::getLogger()->error(MESSAGE_UNAUTHORIZED);
		}
		res = 401;
	}
	catch (const std::exception &ex)
	{
		if (logMessage)
		{
			Logger::getLogger()->error("PI Web API system information exception: %s", ex.what());
		}
		res = 400;
	}
	catch (...)
	{
		if (logMessage)
		{
			Logger::getLogger()->error("PI Web API system information generic exception");
		}
		res = 400;
	}

	m_sender->setMaxRetries(retries);
	return res;
}

/**
 * Calls the Edge Data Store product information endpoint to get the EDS version
 * 
 * @param    logMessage	If true, log error messages (default: true)
 * @return   HttpCode	REST response code
 */
int OMFInformation::EDSGetVersion(bool logMessage)
{
	int res = 400;
	unsigned int retries = m_sender->getMaxRetries();
	m_sender->setMaxRetries(0);

	try
	{
		string path = "http://" + m_hostAndPort + "/api/v1/diagnostics/productinformation";
		
		vector<pair<string, string>> headers;
		headers.push_back( std::make_pair("Accept", "application/json"));

		m_RestServerVersion.clear();

		res = m_sender->sendRequest("GET", path, headers, std::string(""));
		if (res >= 200 && res <= 299)
		{
			m_RestServerVersion = ParseEDSProductInformation(m_sender->getHTTPResponse());
		}
	}
	catch (const BadRequest &ex)
	{
		if (logMessage)
		{
			Logger::getLogger()->error("Edge Data Store productinformation BadRequest exception: %s", ex.what());
		}
		res = 400;
	}
	catch (const Unauthorized &e)
	{
		if (logMessage)
		{
			Logger::getLogger()->error(MESSAGE_UNAUTHORIZED);
		}
		res = 401;
	}
	catch (const std::exception &ex)
	{
		if (logMessage)
		{
			Logger::getLogger()->error("Edge Data Store productinformation exception: %s", ex.what());
		}
		res = 400;
	}
	catch (...)
	{
		if (logMessage)
		{
			Logger::getLogger()->error("Edge Data Store productinformation generic exception");
		}
		res = 400;
	}

	m_sender->setMaxRetries(retries);
	return res;
}

/**
 * Calls the ADH Namespace identity endpoint to check the connection to ADH
 *
 * @param    logMessage	If true, log error messages (default: true)
 * @return   HttpCode	REST response code
 */
int OMFInformation::IsADHConnected(bool logMessage)
{
	if (m_OCSToken.empty())
	{
		std::string token = m_ocs->OCSRetrieveAuthToken(m_OCSClientId, m_OCSClientSecret, false);
		if (!token.empty())
		{
			m_OCSToken = token;
			m_sender->setOCSToken(token);
		}
	}

	int res = 400;
	unsigned int retries = m_sender->getMaxRetries();
	m_sender->setMaxRetries(0);

	try
	{
		string path = m_path;
		path.resize(path.size() - 4); // remove trailing "/omf"

		vector<pair<string, string>> headers;
		headers.push_back( std::make_pair("Accept", "application/json"));

		res = m_sender->sendRequest("GET", path, headers, std::string(""));
	}
	catch (const BadRequest &ex)
	{
		if (logMessage)
		{
			Logger::getLogger()->error("AVEVA Data Hub health check BadRequest exception: %s", ex.what());
		}
		res = 400;
	}
	catch (const Unauthorized &e)
	{
		// HTTP 401: Land here if the ADH or OCS Token has expired
		if (logMessage)
		{
			Logger::getLogger()->error(MESSAGE_UNAUTHORIZED);
		}
		res = 401;
	}
	catch (const std::exception &ex)
	{
		if (logMessage)
		{
			Logger::getLogger()->error("AVEVA Data Hub health check exception: %s", ex.what());
		}
		res = 400;
	}
	catch (...)
	{
		if (logMessage)
		{
			Logger::getLogger()->error("AVEVA Data Hub health check generic exception");
		}
		res = 400;
	}

	m_sender->setMaxRetries(retries);
	return res;
}

/**
 * Set the supported OMF Version for the OMF endpoint 
 */
void OMFInformation::SetOMFVersion()
{
	switch (m_PIServerEndpoint)
	{
	case ENDPOINT_PIWEB_API:
		if (m_RestServerVersion.find("2019") != std::string::npos)
		{
			m_omfversion = "1.0";
		}
		else if (m_RestServerVersion.find("2020") != std::string::npos)
		{
			m_omfversion = "1.1";
		}
		else if (m_RestServerVersion.find("2021") != std::string::npos)
		{
			m_omfversion = "1.2";
		}
		else
		{
			m_omfversion = "1.2";
		}
		break;
	case ENDPOINT_EDS:
		// Edge Data Store versions with supported OMF versions:
		// EDS 2020 (1.0.0.609)				OMF 1.0, 1.1
		// EDS 2023 (1.1.1.46)				OMF 1.0, 1.1, 1.2
		// EDS 2023 Patch 1 (1.1.3.2)		OMF 1.0, 1.1, 1.2
		{
			int major = 0;
			int minor = 0;
			ParseProductVersion(m_RestServerVersion, &major, &minor);
			if ((major > 1) || (major == 1 && minor > 0))
			{
				m_omfversion = "1.2";
			}
			else
			{
				m_omfversion = EDS_OMF_VERSION;
			}
		}
		break;
	case ENDPOINT_CR:
		m_omfversion = CR_OMF_VERSION;
		break;
	case ENDPOINT_OCS:
	case ENDPOINT_ADH:
	default:
		m_omfversion = "1.2"; // assume cloud service OMF endpoint types support OMF 1.2
		break;
	}
}

/**
 * Check the Action code for OMF Data messages.
 * This method changes the Action code only if 'update' is specified for an OMF version too old to support it.
 */
void OMFInformation::CheckDataActionCode()
{
	if (!m_omfversion.empty())
	{
		if ((m_omfversion.compare("1.2") != 0) && (m_dataActionCode.compare("update") == 0))
		{
			Logger::getLogger()->warn("OMF Version %s does not support Data Action Code %s; setting to 'create'", m_omfversion.c_str(), m_dataActionCode.c_str());
			m_dataActionCode = "create";
		}
	}
}

/**
 * Evaluate if the endpoint is a PI Web API or a Connector Relay.
 *
 * @return	               OMF_ENDPOINT values
 */
OMF_ENDPOINT OMFInformation::identifyPIServerEndpoint()
{
	OMF_ENDPOINT PIServerEndpoint;

	HttpSender *endPoint;
	vector<pair<string, string>> header;
	int httpCode;


	if (m_PIWebAPIAuthMethod.compare("k") == 0)
	{
		endPoint = new LibcurlHttps(m_hostAndPort,
					    m_timeout,
					    m_timeout,
					    m_retrySleepTime,
					    m_maxRetry);
	}
	else
	{
		endPoint = new SimpleHttps(m_hostAndPort,
					   m_timeout,
					   m_timeout,
					   m_retrySleepTime,
					   m_maxRetry);
	}

	// Set requested authentication
	endPoint->setAuthMethod          (m_PIWebAPIAuthMethod);
	endPoint->setAuthBasicCredentials(m_PIWebAPICredentials);

	try
	{
		httpCode = endPoint->sendRequest("GET",
						 m_path,
						 header,
						 "");

		if (httpCode >= 200 && httpCode <= 399)
		{
			PIServerEndpoint = ENDPOINT_PIWEB_API;
			if (m_PIWebAPIAuthMethod == "b")
				Logger::getLogger()->debug("PI Web API end-point basic authorization granted");
		}
		else
		{
			PIServerEndpoint = ENDPOINT_CR;
		}

	}
	catch (exception &ex)
	{
		Logger::getLogger()->warn("PI-Server end-point discovery encountered the error :%s: "
			                  "trying selecting the Connector Relay as an end-point", ex.what());
		PIServerEndpoint = ENDPOINT_CR;
	}

	delete endPoint;

	return (PIServerEndpoint);
}


/**
 * Return a JSON string with the dataTypes to save in plugin_data
 *
 * Note: the entry with FAKE_ASSET_KEY is never saved.
 *
 * @return            The string with JSON data
 */
string OMFInformation::saveSentDataTypes()
{
	string ret;
	std::ostringstream newData;

	auto it = m_assetsDataTypes.find(FAKE_ASSET_KEY);
	if (it != m_assetsDataTypes.end())
	{
		// Set typeId in FAKE_ASSET_KEY
		m_typeId = (*it).second.typeId;
		// Remove the entry
		m_assetsDataTypes.erase(it);
	}


	unsigned long tSize = m_assetsDataTypes.size();
	if (tSize)
	{
		
		// Prepare output data (skip empty data types)
		newData << "\"" << SENT_TYPES_KEY << "\" : [";

		bool pendingSeparator = false;
		for (auto it = m_assetsDataTypes.begin();
			  it != m_assetsDataTypes.end();
			  ++it)
		{
			if (((*it).second).types.compare("{}") != 0)
			{
				newData << (pendingSeparator ? ", " : "");
				newData << "{\"" << (*it).first << "\" : {\"" << TYPE_ID_KEY <<
					   "\": " << to_string(((*it).second).typeId);

				// The information should be stored as string in hexadecimal format
				std::stringstream tmpStream;
				tmpStream << std::hex << ((*it).second).typesShort;
				std::string typesShort = tmpStream.str();

				newData << ", \"" << DATA_KEY_SHORT << "\": \"0x" << typesShort << "\"";
				std::stringstream hintStream;
				hintStream << std::hex << ((*it).second).hintChkSum;
				std::string hintChecksum = hintStream.str();
				newData << ", \"" << DATA_KEY_HINT << "\": \"0x" << hintChecksum << "\"";

				long NamingScheme;
				NamingScheme = ((*it).second).namingScheme;
				newData << ", \"" << NAMING_SCHEME << "\": " << to_string(NamingScheme) << "";

				string AFHHash;
				AFHHash = ((*it).second).afhHash;
				newData << ", \"" << AFH_HASH << "\": \"" << AFHHash << "\"";

				string AFHierarchy;
				AFHierarchy = ((*it).second).afHierarchy;
				newData << ", \"" << AF_HIERARCHY << "\": \"" << AFHierarchy << "\"";

				string AFHierarchyOrig;
				AFHierarchyOrig = ((*it).second).afHierarchyOrig;
				newData << ", \"" << AF_HIERARCHY_ORIG << "\": \"" << AFHierarchyOrig << "\"";

				Logger::getLogger()->debug("%s - AFHHash :%s: AFHierarchy :%s: AFHierarchyOrig :%s:", __FUNCTION__, AFHHash.c_str(), AFHierarchy.c_str(), AFHierarchyOrig.c_str()  );
				Logger::getLogger()->debug("%s - NamingScheme :%ld: ", __FUNCTION__,NamingScheme );

				newData << ", \"" << DATA_KEY << "\": " <<
					   (((*it).second).types.empty() ? "{}" : ((*it).second).types) <<
					   "}}";
				pendingSeparator = true;
			}
		}

		tSize = m_assetsDataTypes.size();
		if (!tSize)
		{
			// DataTypes map is empty
			return ret;
		}

		newData << "]";

		ret = newData.str();
	}

	return ret;
}


/**
 * Calculate the TypeShort in the case it is missing loading type definition
 *
 * Generate a 64 bit number containing a set of counts,
 * number of datapoints in an asset and the number of datapoint of each type we support.
 *
 */
unsigned long OMFInformation::calcTypeShort(const string& dataTypes)
{
	union t_typeCount {
		struct
		{
			unsigned char tTotal;
			unsigned char tFloat;
			unsigned char tString;
			unsigned char spare0;

			unsigned char spare1;
			unsigned char spare2;
			unsigned char spare3;
			unsigned char spare4;
		} cnt;
		unsigned long valueLong = 0;

	} typeCount;

	Document JSONData;
	JSONData.Parse(dataTypes.c_str());

	if (JSONData.HasParseError())
	{
		Logger::getLogger()->error("calcTypeShort - unable to calculate TypeShort on :%s: ", dataTypes.c_str());
		return (0);
	}

	for (Value::ConstMemberIterator it = JSONData.MemberBegin(); it != JSONData.MemberEnd(); ++it)
	{

		string key = it->name.GetString();
		const Value& value = it->value;

		if (value.HasMember(PROPERTY_TYPE) && value[PROPERTY_TYPE].IsString())
		{
			string type =value[PROPERTY_TYPE].GetString();

			// Integer is handled as float in the OMF integration
			if (type.compare(PROPERTY_NUMBER) == 0)
			{
				typeCount.cnt.tFloat++;
			} else if (type.compare(PROPERTY_STRING) == 0)
			{
				typeCount.cnt.tString++;
			} else {

				Logger::getLogger()->error("calcTypeShort - unrecognized type :%s: ", type.c_str());
			}
			typeCount.cnt.tTotal++;
		}
		else
		{
			Logger::getLogger()->error("calcTypeShort - unable to extract the type for :%s: ", key.c_str());
			return (0);
		}
	}

	return typeCount.valueLong;
}

/**
 * Finds major and minor product version numbers in a version string
 * 
 * @param    versionString		Version string of the form x.x.x.x where x's are integers
 * @param    major				Major product version returned (first digit)
 * @param    minor				Minor product version returned (second digit)
 */
void OMFInformation::ParseProductVersion(std::string &versionString, int *major, int *minor)
{
	*major = 0;
	*minor = 0;
	size_t last = 0;
	size_t next = versionString.find(".", last);
	if (next != string::npos)
	{
		*major = atoi(versionString.substr(last, next - last).c_str());
		last = next + 1;
		next = versionString.find(".", last);
		if (next != string::npos)
		{
			*minor = atoi(versionString.substr(last, next - last).c_str());
		}
	}
}

/**
 * Parses the Edge Data Store version string from the /productinformation REST response.
 * Note that the response format differs between EDS 2020 and EDS 2023.
 * 
 * @param    json		REST response from /api/v1/diagnostics/productinformation
 * @return   version	Edge Data Store version string
 */
std::string OMFInformation::ParseEDSProductInformation(std::string json)
{
	std::string version;

	Document doc;

	if (!doc.Parse(json.c_str()).HasParseError())
	{
		try
		{
			if (doc.HasMember("Edge Data Store"))	// EDS 2020 response
			{
				const rapidjson::Value &EDS = doc["Edge Data Store"];
				version = EDS.GetString();
			}
			else if (doc.HasMember("Product Version"))	// EDS 2023 response
			{
				const rapidjson::Value &EDS = doc["Product Version"];
				version = EDS.GetString();
			}
		}
		catch (...)
		{
		}
	}

	Logger::getLogger()->debug("Edge Data Store Version: %s JSON: %s", version.c_str(), json.c_str());
	return version;
}

/**
 * Generate the credentials for the basic authentication
 * encoding user id and password joined by a single colon (:) using base64
 *
 * @param    userId   User id to be used for the generation of the credentials
 * @param    password Password to be used for the generation of the credentials
 * @return            credentials to be used with the basic authentication
 */
string OMFInformation::AuthBasicCredentialsGenerate(string& userId, string& password)
{
	string Credentials;

	Credentials = Crypto::Base64::encode(userId + ":" + password);
	              	
	return (Credentials);
}

/**
 * Configures for Kerberos authentication :
 *   - set the environment KRB5_CLIENT_KTNAME to the position containing the
 *     Kerberos keys, the keytab file.
 *
 * @param   out  keytabEnv       string containing the command to set the
 *                               KRB5_CLIENT_KTNAME environment variable
 * @param        keytabFileName  File name of the keytab file
 *
 */
void OMFInformation::AuthKerberosSetup(string& keytabEnv, string& keytabFileName)
{
	string fledgeData = getDataDir ();
	string keytabFullPath = fledgeData + "/etc/kerberos" + "/" + keytabFileName;

	keytabEnv = "KRB5_CLIENT_KTNAME=" + keytabFullPath;
	putenv((char *) keytabEnv.c_str());

	if (access(keytabFullPath.c_str(), F_OK) != 0)
	{
		Logger::getLogger()->error("Kerberos authentication not possible, the keytab file :%s: is missing.", keytabFullPath.c_str());
	}

}

/**
 * Calculate elapsed time in seconds
 *
 * @param startTime   Start time of the interval to be evaluated
 * @return            Elapsed time in seconds
 */
double OMFInformation::GetElapsedTime(struct timeval *startTime)
{
	struct timeval endTime, diff;
	gettimeofday(&endTime, NULL);
	timersub(&endTime, startTime, &diff);
	return diff.tv_sec + ((double)diff.tv_usec / 1000000);
}

/**
 * Check if the destination data archive is available by making a lightweight REST GET call every 60 seconds.
 * Log a message if the connection state changes.
 * First call to this method will make a REST call.
 * This method can check connectivity with PI Web API, Edge Data Store and AVEVA Data Hub.
 *
 * @return           Connection status
 */
bool OMFInformation::IsDataArchiveConnected()
{
	static std::chrono::steady_clock::time_point nextCheck(std::chrono::steady_clock::time_point::duration::zero());
	static bool lastConnected = m_connected; // Previous value of m_connected

	std::chrono::steady_clock::time_point now = std::chrono::steady_clock::now();

	if (now >= nextCheck)
	{
		int httpCode;

		switch (m_PIServerEndpoint)
		{
		case ENDPOINT_PIWEB_API:
			httpCode = PIWebAPIGetVersion(false);
			break;
		case ENDPOINT_EDS:
			httpCode = EDSGetVersion(false);
			break;
		case ENDPOINT_ADH:
		case ENDPOINT_OCS:
			httpCode = IsADHConnected(false);
			break;
		default:
			httpCode = 200; // assume all other endpoint types are connected
			break;
		}

		m_connected = ((httpCode < 200) || (httpCode >= 400)) ? false : true;

		Logger::getLogger()->debug("%s: Check %s HTTP Code: %d Connected: %s LastConnected: %s",
								   __FUNCTION__,
								   m_hostAndPort.c_str(),
								   httpCode,
								   m_connected ? "true" : "false",
								   lastConnected ? "true" : "false");

		// See if the connection status has changed since the last check.
		// If so, write a disconnection or reconnection message.
		if (m_connected == true)
		{
			SetOMFVersion();
			CheckDataActionCode();

			if (lastConnected == false)
			{
				switch (m_PIServerEndpoint)
				{
				case ENDPOINT_PIWEB_API:
					Logger::getLogger()->warn("%s reconnected to %s OMF Version: %s",
											  m_RestServerVersion.c_str(), m_hostAndPort.c_str(), m_omfversion.c_str());
					break;
				case ENDPOINT_EDS:
					Logger::getLogger()->warn("Edge Data Store %s reconnected to %s OMF Version: %s",
											  m_RestServerVersion.c_str(), m_hostAndPort.c_str(), m_omfversion.c_str());
					break;
				case ENDPOINT_ADH:
					Logger::getLogger()->warn("AVEVA Data Hub %s reconnected. OMF Version: %s",
											  m_hostAndPort.c_str(), m_omfversion.c_str());
					break;
				case ENDPOINT_OCS:
					Logger::getLogger()->warn("OSIsoft Cloud Services %s reconnected. OMF Version: %s",
											  m_hostAndPort.c_str(), m_omfversion.c_str());
					break;
				default:
					Logger::getLogger()->warn("Destination Data Archive %s reconnected. OMF Version: %s",
											  m_hostAndPort.c_str(), m_omfversion.c_str());
					break;
				}

				lastConnected = true;
			}
		}
		else
		{
			if (lastConnected == true)
			{
				switch (m_PIServerEndpoint)
				{
				case ENDPOINT_PIWEB_API:
					Logger::getLogger()->error("The PI Web API service %s is not available. HTTP Code: %d",
											   m_hostAndPort.c_str(), httpCode);
					break;
				case ENDPOINT_EDS:
					Logger::getLogger()->error("Edge Data Store %s is not available. HTTP Code: %d",
											   m_hostAndPort.c_str(), httpCode);
					break;
				case ENDPOINT_ADH:
					Logger::getLogger()->error("AVEVA Data Hub %s is not available. HTTP Code: %d",
											   m_hostAndPort.c_str(), httpCode);
					break;
				case ENDPOINT_OCS:
					Logger::getLogger()->error("OSIsoft Cloud Services %s is not available. HTTP Code: %d",
											   m_hostAndPort.c_str(), httpCode);
					break;
				default:
					Logger::getLogger()->warn("Destination Data Archive %s is not available. HTTP Code: %d",
											  m_hostAndPort.c_str(), httpCode);
					break;
				}

				lastConnected = false;
			}
		}

		nextCheck = now + std::chrono::seconds(60);
	}

	return m_connected;
}

/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <south_service.h>
#include <management_api.h>
#include <storage_client.h>
#include <service_record.h>
#include <plugin_manager.h>
#include <plugin_api.h>
#include <plugin.h>
#include <logger.h>
#include <reading.h>
#include <ingest.h>
#include <iostream>
#include <defaults.h>
#include <filter_plugin.h>

extern int makeDaemon(void);

using namespace std;

/**
 * South service main entry point
 */
int main(int argc, char *argv[])
{
unsigned short corePort = 8082;
string	       coreAddress = "localhost";
bool	       daemonMode = true;
string	       myName = SERVICE_NAME;

	for (int i = 1; i < argc; i++)
	{
		if (!strcmp(argv[i], "-d"))
		{
			daemonMode = false;
		}
		else if (!strncmp(argv[i], "--port=", 7))
		{
			corePort = (unsigned short)atoi(&argv[i][7]);
		}
		else if (!strncmp(argv[i], "--name=", 7))
		{
			myName = &argv[i][7];
		}
		else if (!strncmp(argv[i], "--address=", 10))
		{
			coreAddress = &argv[i][10];
		}
	}

	if (daemonMode && makeDaemon() == -1)
	{
		// Failed to run in daemon mode
		cout << "Failed to run as deamon - proceeding in interactive mode." << endl;
	}

	SouthService *service = new SouthService(myName);
	service->start(coreAddress, corePort);
	return 0;
}

/**
 * Detach the process from the terminal and run in the background.
 */
int makeDaemon()
{
pid_t pid;

	/* create new process */
	if ((pid = fork()  ) == -1)
	{
		return -1;  
	}
	else if (pid != 0)  
	{
		exit (EXIT_SUCCESS);  
	}

	// If we got here we are a child process

	// create new session and process group 
	if (setsid() == -1)  
	{
		return -1;  
	}

	// Close stdin, stdout and stderr
	close(0);
	close(1);
	close(2);
	// redirect fd's 0,1,2 to /dev/null
	(void)open("/dev/null", O_RDWR);  	// stdin
	(void)dup(0);  			// stdout	GCC bug 66425 produces warning
	(void)dup(0);  			// stderr	GCC bug 66425 produces warning
 	return 0;
}

/**
 * Constructor for the south service
 */
SouthService::SouthService(const string& myName) : m_name(myName), m_shutdown(false), m_pollInterval(1000)
{
	logger = new Logger(myName);
}

/**
 * Start the south service
 */
void SouthService::start(string& coreAddress, unsigned short corePort)
{
	unsigned short managementPort = (unsigned short)0;
	ManagementApi management(SERVICE_NAME, managementPort);	// Start managemenrt API
	logger->info("Starting south service...");
	management.registerService(this);

	// Listen for incomming managment requests
	management.start();

	// Allow time for the listeners to start before we register
	sleep(1);
	if (! m_shutdown)
	{
		// Now register our service
		// TODO proper hostname lookup
		unsigned short managementListener = management.getListenerPort();
		ServiceRecord record(m_name, "Southbound", "http", "localhost", 0, managementListener);
		m_mgtClient = new ManagementClient(coreAddress, corePort);

		// Create an empty South category if one doesn't exist
		DefaultConfigCategory southConfig(string("South"), string("{}"));
		southConfig.setDescription("South");
		m_mgtClient->addCategory(southConfig, true);

		m_config = m_mgtClient->getCategory(m_name);
		if (!loadPlugin())
		{
			logger->fatal("Failed to load south plugin.");
			return;
		}
		if (!m_mgtClient->registerService(record))
		{
			logger->error("Failed to register service %s", m_name.c_str());
		}
		unsigned int retryCount = 0;
		while (m_mgtClient->registerCategory(m_name) == false && ++retryCount < 10)
		{
			sleep(2 * retryCount);
		}

		// Get a handle on the storage layer
		ServiceRecord storageRecord("FogLAMP%20Storage");
		if (!m_mgtClient->getService(storageRecord))
		{
			logger->fatal("Unable to find storage service");
			return;
		}
		logger->info("Connect to storage on %s:%d",
				storageRecord.getAddress().c_str(),
				storageRecord.getPort());

		
		StorageClient storage(storageRecord.getAddress(),
						storageRecord.getPort());
		unsigned int threshold = 100;
		unsigned long timeout = 5000;
		try {
			if (m_config.itemExists("bufferThreshold"))
				threshold = (unsigned int)atoi(m_config.getValue("bufferThreshold").c_str());
			if (m_config.itemExists("maxSendLatency"))
				timeout = (unsigned long)atoi(m_config.getValue("maxSendLatency").c_str());
		} catch (ConfigItemNotFound e) {
			logger->info("Defaulting to inline defaults for south configuration");
		}

		// Instantiate the Ingest class
		Ingest ingest(storage, timeout, threshold);

		try {
			m_pollInterval = 500;
			if (m_config.itemExists("pollInterval"))
				m_pollInterval = (unsigned long)atoi(m_config.getValue("pollInterval").c_str());
		} catch (ConfigItemNotFound e) {
			logger->info("Defaulting to inline default for poll interval");
		}

		// Load filter plugins and set them in the Ingest class
		if (!this->loadFilters(m_name, ingest))
		{
			string errMsg("'" + m_name + "' plugin: failed loading filter plugins.");
			Logger::getLogger()->fatal((errMsg + " Exiting.").c_str());
			throw runtime_error(errMsg);
		}

		// Get and ingest data
		while (!m_shutdown)
		{
			std::this_thread::sleep_for(std::chrono::milliseconds(m_pollInterval));
			Reading reading = southPlugin->poll();
			ingest.ingest(reading);
		}

		// Clean shutdown, unregister the storage service
		m_mgtClient->unregisterService();
	}
	logger->info("South service shut down.");
}

/**
 * Stop the storage service/
 */
void SouthService::stop()
{
	logger->info("Stopping south service...\n");
}

/**
 * Load the configured south plugin
 *
 * TODO Should search for the plugin in specified locations
 */
bool SouthService::loadPlugin()
{
	try {
		PluginManager *manager = PluginManager::getInstance();

		if (! m_config.itemExists("plugin"))
		{
			logger->error("Unable to fetch plugin name from configuration.\n");
			return false;
		}
		string plugin = m_config.getValue("plugin");
		logger->info("Loading south plugin %s.", plugin.c_str());
		PLUGIN_HANDLE handle;
		if ((handle = manager->loadPlugin(plugin, PLUGIN_TYPE_SOUTH)) != NULL)
		{
			// Deal with registering and fetching the configuration
			DefaultConfigCategory defConfig(m_name, manager->getInfo(handle)->config);
			addConfigDefaults(defConfig);
			defConfig.setDescription(m_name);	// TODO We do not have access to the description

			// Create/Update category name (we pass keep_original_items=true)
			m_mgtClient->addCategory(defConfig, true);

			// Add this service under 'South' parent category
			vector<string> children;
			children.push_back(m_name);
			m_mgtClient->addChildCategories(string("South"), children);

			// Must now reload the configuration to obtain any items added from
			// the plugin
			m_config = m_mgtClient->getCategory(m_name);
			
			southPlugin = new SouthPlugin(handle, m_config);
			logger->info("Loaded south plugin %s.", plugin.c_str());
			return true;
		}
	} catch (exception e) {
		logger->fatal("Failed to load south plugin: %s\n", e.what());
	}
	return false;
}

/**
 * Shutdown request
 */
void SouthService::shutdown()
{
	/* Stop recieving new requests and allow existing
	 * requests to drain.
	 */
	m_shutdown = true;
	logger->info("South service shutdown in progress.");
}

/**
 * Configuration change notification
 */
void SouthService::configChange(const string& categoryName, const string& category)
{
	// TODO action configuration change
	logger->info("Configuration change in category %s: %s", categoryName.c_str(),
			category.c_str());
	m_config = m_mgtClient->getCategory(m_name);
	try {
		m_pollInterval = (unsigned long)atoi(m_config.getValue("pollInterval").c_str());
	} catch (ConfigItemNotFound e) {
		logger->error("Failed to update poll interval following configuration change");
	}
}

/**
 * Add the generic south service configuration options to the default retrieved
 * from the specific plugin.
 *
 * @param defaultConfiguration	The default configuration from the plugin
 */
void SouthService::addConfigDefaults(DefaultConfigCategory& defaultConfig)
{
	for (int i = 0; defaults[i].name; i++)
	{
		defaultConfig.addItem(defaults[i].name, defaults[i].description,
			defaults[i].type, defaults[i].value, defaults[i].value);	
	}
}

/**
 * Load filter plugins
 *
 * Filters found in configuration are loaded
 * and adde to the Ingest class instance
 *
 * @param categoryName	Configuration category name
 * @param ingest	The Ingest class reference
 *			Filters are added to m_filters member
 *			False for errors.
 * @return		True if filters were loaded and initialised
 *			or there are no filters
 *			False with load/init errors
 */
bool SouthService::loadFilters(const string& categoryName,
			       Ingest& ingest) const
{
	// Try to load filters:
	if (!FilterPlugin::loadFilters(categoryName,
				       ingest.m_filters,
				       m_mgtClient))
	{
		// Return false on any error
		return false;
	}

	// Set up the filter pipeline
	return this->setupFiltersPipeline(ingest);
}

/**
 * Set the filterPipeline in the Ingest class
 * 
 * This method calls the the method "plugin_init" for all loadade filters.
 * Up to date filter configurations and Ingest filtering methods
 * are passed to "plugin_init"
 *
 * @param ingest	The ingest class
 * @return 		True on success,
 *			False otherwise.
 * @thown		Any caught exception
 */
bool SouthService::setupFiltersPipeline(const Ingest& ingest) const
{
	bool initErrors = false;
	string errMsg = "'plugin_init' failed for filter '";
	for (auto it = ingest.m_filters.begin(); it != ingest.m_filters.end(); ++it)
	{
		string filterCategoryName = m_name;
		filterCategoryName.append("_");
		filterCategoryName += (*it)->getName();
		filterCategoryName.append("Filter");

		ConfigCategory updatedCfg;
		vector<string> children;
        
		try
		{
			// Fetch up to date filter configuration
			updatedCfg = m_mgtClient->getCategory(filterCategoryName);

			// Add filter category name under service/process config name
			children.push_back(filterCategoryName);
			m_mgtClient->addChildCategories(m_name, children);
		}
		// TODO catch specific exceptions
		catch (...)
		{       
			throw;      
		}                   

		// Iterate the load filters set in the Ingest class m_filters member 
		if ((it + 1) != ingest.m_filters.end())
		{
			// Set next filter pointer as OUTPUT_HANDLE
			if (!(*it)->init(updatedCfg,
				    (OUTPUT_HANDLE *)(*(it + 1)),
				    Ingest::passToOnwardFilter))
			{
				errMsg += (*it)->getName() + "'";
				initErrors = true;
				break;
			}
		}
		else
		{
			// Set the Ingest class pointer as OUTPUT_HANDLE
			if (!(*it)->init(updatedCfg,
					 (OUTPUT_HANDLE *)&ingest,
					 Ingest::useFilteredData))
			{
				errMsg += (*it)->getName() + "'";
				initErrors = true;
				break;
			}
		}
	}

	if (initErrors)
	{
		// Failure
		logger->fatal("%s error: %s", SERVICE_NAME, errMsg.c_str());
		return false;
	}

	//Success
	return true;
}

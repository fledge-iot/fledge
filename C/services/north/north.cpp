/*
 * Fledge north service.
 *
 * Copyright (c) 2020 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <sys/timerfd.h>
#include <time.h>
#include <stdint.h>
#include <stdlib.h>
#include <signal.h>
#include <execinfo.h>
#include <dlfcn.h>    // for dladdr
#include <cxxabi.h>   // for __cxa_demangle
#include <unistd.h>
#include <north_service.h>
#include <management_api.h>
#include <storage_client.h>
#include <service_record.h>
#include <plugin_manager.h>
#include <plugin_api.h>
#include <plugin.h>
#include <logger.h>
#include <reading.h>
#include <data_load.h>
#include <data_sender.h>
#include <iostream>
#include <defaults.h>
#include <filter_plugin.h>
#include <config_handler.h>
#include <syslog.h>
#include <stdarg.h>
#include <string_utils.h>
#include <audit_logger.h>

#define SERVICE_TYPE "Northbound"

extern int makeDaemon(void);
extern void handler(int sig);

static const char *defaultServiceConfig = QUOTE({
	"enable": {
		"description": "A switch that can be used to enable or disable execution of the sending process.",
		"type": "boolean",
		"default": "true" ,
		"readonly": "true"
		},
	"streamId": {
		"description": "Identifies the specific stream to handle and the related information, among them the ID of the last object streamed.",
		"type": "integer",
		"default": "0",
		"readonly": "true"
		 }
		});

using namespace std;

static NorthService *service;

/**
 * Callback function when a plugin wishes to perform a write operation
 *
 * @param name	The name of the value to write
 * @param value	The value to write
 * @param destination	Where to write the value
 */
static bool controlWrite(char *name, char *value, ControlDestination destination, ...)
{
	va_list ap;
	bool rval = false;

	switch (destination)
	{
		case DestinationAsset:
		case DestinationService:
		case DestinationScript:
		{
			va_start(ap, destination);
			char *arg1 = va_arg(ap, char *);
			va_end(ap);
			rval = service->write(name, value, destination, arg1);
			break;
		}
		case DestinationBroadcast:
			rval = service->write(name, value, destination);
			break;
		default:
			Logger::getLogger()->error("Unknown control write destination %d", destination);
	}
	return rval;
}

/**
 * Callback function when a plugin wishes to perform a control operation
 *
 * @param operation	The name of the operation to perform
 * @param paramCount	The count of the number of parameters
 * @param names		The names of the parameters
 * @param parameters	The values of the parameters
 * @param destiantion	The destiantion for the operation
 */
static int controlOperation(char *operation, int paramCount, char *names[], char *parameters[], ControlDestination destination, ...)
{
	va_list ap;
	int	rval = -1;

	switch (destination)
	{
		case DestinationAsset:
		case DestinationService:
			va_start(ap, destination);
			rval = service->operation(operation, paramCount, names, parameters, destination, va_arg(ap, char *));
			va_end(ap);
			break;
		case DestinationBroadcast:
			rval = service->operation(operation, paramCount, names, parameters, destination);
			break;
		default:
			Logger::getLogger()->error("Unknown control operation destination %d for operation %s", destination, operation);
	}
	return rval;
}

/**
 * North service main entry point
 */
int main(int argc, char *argv[])
{
unsigned short	corePort = 8082;
string		coreAddress = "localhost";
bool		daemonMode = true;
string		myName = SERVICE_NAME;
string		logLevel = "warning";
string		token = "";
bool		dryRun = false;

	signal(SIGSEGV, handler);
	signal(SIGILL, handler);
	signal(SIGBUS, handler);
	signal(SIGFPE, handler);
	signal(SIGABRT, handler);

	for (int i = 1; i < argc; i++)
	{
		if (!strcmp(argv[i], "-d"))
		{
			daemonMode = false;
		}
		else if (!strncmp(argv[i], "--port=", 7))
		{
			corePort = (unsigned short)strtol(&argv[i][7], NULL, 10);
		}
		else if (!strncmp(argv[i], "--name=", 7))
		{
			myName = &argv[i][7];
		}
		else if (!strncmp(argv[i], "--address=", 10))
		{
			coreAddress = &argv[i][10];
		}
		else if (!strncmp(argv[i], "--logLevel=", 11))
		{
			logLevel = &argv[i][11];
		}
		else if (!strncmp(argv[i], "--token=", 8))
		{
			token = &argv[i][8];
		}
		else if (!strncmp(argv[i], "--dryrun", 8))
		{
			dryRun = true;
		}
	}

	if (daemonMode && makeDaemon() == -1)
	{
		// Failed to run in daemon mode
		cout << "Failed to run as deamon - proceeding in interactive mode." << endl;
	}

	service = new NorthService(myName, token);
	if (dryRun)
	{
		service->setDryRun();
	}
	Logger::getLogger()->setMinLevel(logLevel);
	service->start(coreAddress, corePort);

	delete service;
	return 0;
}

/**
 * Detach the process from the terminal and run in the background.
 */
int makeDaemon()
{
pid_t pid;

	/* Make the child process inherit the log level */
	int logmask = setlogmask(0);
	/* create new process */
	if ((pid = fork()  ) == -1)
	{
		return -1;  
	}
	else if (pid != 0)  
	{
		exit (EXIT_SUCCESS);  
	}
	setlogmask(logmask);

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
	open("/dev/null", O_RDWR);  	// stdin
	if (dup(0) == -1) {}  		// stdout	GCC bug 66425 produces warning
	if (dup(0) == -1) {}  		// stderr	GCC bug 66425 produces warning
 	return 0;
}

void handler(int sig)
{
Logger	*logger = Logger::getLogger();
void	*array[20];
char	buf[1024];
int	size;

	// get void*'s for all entries on the stack
	size = backtrace(array, 20);

	// print out all the frames to stderr
	logger->fatal("Signal %d (%s) trapped:\n", sig, strsignal(sig));
	char **messages = backtrace_symbols(array, size);
	for (int i = 0; i < size; i++)
	{
		Dl_info info;
		if (dladdr(array[i], &info) && info.dli_sname)
		{
		    char *demangled = NULL;
		    int status = -1;
		    if (info.dli_sname[0] == '_')
		        demangled = abi::__cxa_demangle(info.dli_sname, NULL, 0, &status);
		    snprintf(buf, sizeof(buf), "%-3d %*p %s + %zd---------",
		             i, int(2 + sizeof(void*) * 2), array[i],
		             status == 0 ? demangled :
		             info.dli_sname == 0 ? messages[i] : info.dli_sname,
		             (char *)array[i] - (char *)info.dli_saddr);
		    free(demangled);
		} 
		else
		{
		    snprintf(buf, sizeof(buf), "%-3d %*p %s---------",
		             i, int(2 + sizeof(void*) * 2), array[i], messages[i]);
		}
		logger->fatal("(%d) %s", i, buf);
	}
	free(messages);
	exit(1);
}
		

/**
 * Constructor for the north service
 */
NorthService::NorthService(const string& myName, const string& token) :
	m_dataLoad(NULL),
	m_dataSender(NULL),
	northPlugin(NULL),
	m_assetTracker(NULL),
	m_shutdown(false),
	m_storage(NULL),
	m_pluginData(NULL),
	m_restartPlugin(false),
	m_token(token),
	m_allowControl(true),
	m_dryRun(false),
	m_requestRestart(),
	m_auditLogger(NULL),
	m_perfMonitor(NULL)
{
	m_name = myName;
	logger = new Logger(myName);
	logger->setMinLevel("warning");
}

/**
 * Destructor for the north service
 */
NorthService::~NorthService()
{
	if (m_perfMonitor)
		delete m_perfMonitor;
	if (northPlugin)
		delete northPlugin;
	if (m_storage)
		delete m_storage;
	if (m_dataLoad)
		delete m_dataLoad;
	if (m_dataSender)
		delete m_dataSender;
	if (m_pluginData)
		delete m_pluginData;
	if (m_assetTracker)
		delete m_assetTracker;
	if (m_auditLogger)
		delete m_auditLogger;
	if (m_mgtClient)
		delete m_mgtClient;
	delete logger;
}

/**
 * Start the north service
 */
void NorthService::start(string& coreAddress, unsigned short corePort)
{
	unsigned short managementPort = (unsigned short)0;
	ManagementApi management(SERVICE_NAME, managementPort);	// Start managemenrt API
	logger->info("Starting north service...");
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
		ServiceRecord record(m_name,		// Service name
				SERVICE_TYPE,		// Service type
				"http",			// Protocol
				"localhost",		// Listening address
				0,			// Service port
				managementListener,	// Management port
				m_token);		// Token);
		m_mgtClient = new ManagementClient(coreAddress, corePort);

		m_auditLogger = new AuditLogger(m_mgtClient);

		// Create an empty North category if one doesn't exist
		DefaultConfigCategory northConfig(string("North"), string("{}"));
		northConfig.setDescription("North");
		m_mgtClient->addCategory(northConfig, true);

		// Fetch Configuration
		m_config = m_mgtClient->getCategory(m_name);
		if (!loadPlugin())
		{
			logger->fatal("Failed to load north plugin, exiting...");
			management.stop();
			return;
		}
		if (!m_dryRun)
		{
			if (!m_mgtClient->registerService(record))
			{
				logger->error("Failed to register service %s", m_name.c_str());
				management.stop();
				return;
			}
			ConfigHandler *configHandler = ConfigHandler::getInstance(m_mgtClient);
			configHandler->registerCategory(this, m_name);
			configHandler->registerCategory(this, m_name+"Advanced");
		}

		// Get a handle on the storage layer
		ServiceRecord storageRecord("Fledge Storage");
		if (!m_mgtClient->getService(storageRecord))
		{
			logger->fatal("Unable to find storage service");
			if (!m_dryRun)
			{

				if (m_requestRestart)
					m_mgtClient->restartService();
				else
					m_mgtClient->unregisterService();
			}
			return;
		}
		logger->info("Connect to storage on %s:%d",
				storageRecord.getAddress().c_str(),
				storageRecord.getPort());

		
		m_storage = new StorageClient(storageRecord.getAddress(),
						storageRecord.getPort());

		m_storage->registerManagement(m_mgtClient);

		// Setup the performance monitor
		m_perfMonitor = new PerformanceMonitor(m_name, m_storage);

		if (m_configAdvanced.itemExists("perfmon"))
		{
			string perf = m_configAdvanced.getValue("perfmon");
			if (perf.compare("true") == 0)
				m_perfMonitor->setCollecting(true);
			else
				m_perfMonitor->setCollecting(false);
		}

		logger->debug("Initialise the asset tracker");
		m_assetTracker = new AssetTracker(m_mgtClient, m_name);
		AssetTracker::getAssetTracker()->populateAssetTrackingCache(m_name, "Egress");

		// If the plugin supports control register the callback functions
		if (northPlugin->hasControl())
		{
			northPlugin->pluginRegister(controlWrite, controlOperation);
		}

		// Deal with persisted data and start the plugin
		if (!m_dryRun)
		{
			if (northPlugin->persistData())
			{
				logger->debug("Plugin %s requires persisted data", m_pluginName.c_str());
				m_pluginData = new PluginData(m_storage);
				string key = m_name + m_pluginName;
				string storedData = m_pluginData->loadStoredData(key);
				logger->debug("Starting plugin with storedData: %s", storedData.c_str());
				northPlugin->startData(storedData);
				
			}
			else
			{
				logger->debug("Start %s plugin", m_pluginName.c_str());
				northPlugin->start();
			}
		}

		// Create default security category
		this->createSecurityCategories(m_mgtClient, m_dryRun);

		// Setup the data loading
		long streamId = 0;
		if (m_config.itemExists("streamId"))
		{
			streamId = strtol(m_config.getValue("streamId").c_str(), NULL, 10);
		}
		logger->debug("Create threads for stream %d", streamId);
		m_dataLoad = new DataLoad(m_name, streamId, m_storage);
		m_dataLoad->setPerfMonitor(m_perfMonitor);
		if (m_config.itemExists("source"))
		{
			m_dataLoad->setDataSource(m_config.getValue("source"));
		}
		if (m_configAdvanced.itemExists("blockSize"))
		{
			unsigned long newBlock = strtoul(
						m_configAdvanced.getValue("blockSize").c_str(),
						NULL,
						10);
			if (newBlock > 0)
			{
				m_dataLoad->setBlockSize(newBlock);
			}
		}
		if (m_configAdvanced.itemExists("assetTrackerInterval"))
		{
			unsigned long interval  = strtoul(
						m_configAdvanced.getValue("assetTrackerInterval").c_str(),
						NULL,
						10);
			if (m_assetTracker)
				m_assetTracker->tune(interval);
		}
		m_dataSender = new DataSender(northPlugin, m_dataLoad, this);
		m_dataSender->setPerfMonitor(m_perfMonitor);

		if (!m_dryRun)
		{
			logger->debug("North service is running");

			
			// wait for shutdown
			unique_lock<mutex> lck(m_mutex);
			while (!m_shutdown)
			{
				m_cv.wait(lck);
				logger->debug("North main thread woken up, shutdown %s", m_shutdown ? "true" : "false");
				if (m_shutdown == false && m_restartPlugin)
				{
					restartPlugin();
				}
			}
			logger->debug("North service is shutting down");
		}
		else
		{
			logger->info("Dryrun of service, shutting down");
		}

		m_dataLoad->shutdown();		// Forces the data load to return from any blocking fetch call
		delete m_dataSender;
		m_dataSender = NULL;
		logger->debug("North service data sender has shut down");
		delete m_dataLoad;
		m_dataLoad = NULL;
		logger->debug("North service shutting down plugin");


		// Shutdown the north plugin
		if (northPlugin && !m_dryRun)
		{
			if (m_pluginData)
			{
				logger->debug("North service persist plugin data");
				string saveData = northPlugin->shutdownSaveData();
				string key = m_name + m_pluginName;
				logger->debug("Persist plugin data key %s is %s", key.c_str(), saveData.c_str());
				if (!m_pluginData->persistPluginData(key, saveData))
				{
					Logger::getLogger()->error("Plugin %s has failed to save data [%s] for key %s",
						m_pluginName.c_str(), saveData.c_str(), key.c_str());
				}
			}
			else
			{
				northPlugin->shutdown();
			}
		}
		
		if (!m_dryRun)
		{
			if (m_requestRestart)
			{
				// Request core to restart this service
				m_mgtClient->restartService();
			} 
			else
			{
				// Clean shutdown, unregister the storage service
				logger->info("Unregistering service");
				m_mgtClient->unregisterService();
			}
		}
	}
	management.stop();
	logger->info("North service %s shutdown completed", m_dryRun ? "dry run execution " : "");
}

/**
 * Stop the storage service/
 */
void NorthService::stop()
{
	logger->info("Stopping north service...\n");
}

/**
 * Creates config categories and sub categories recursively, along with their parent-child relations
 */
void NorthService::createConfigCategories(DefaultConfigCategory configCategory, std::string parent_name, std::string current_name)
{

	// Deal with registering and fetching the configuration
	DefaultConfigCategory defConfig(configCategory);

	DefaultConfigCategory defConfigCategoryOnly(defConfig);
	defConfigCategoryOnly.keepItemsType(ConfigCategory::ItemType::CategoryType);
	defConfig.removeItemsType(ConfigCategory::ItemType::CategoryType);

	DefaultConfigCategory serviceConfig(current_name,
                                               defaultServiceConfig);
	defConfig += serviceConfig;

	defConfig.setDescription(current_name);	// TODO We do not have access to the description
	// Create/Update category name (we pass keep_original_items=true)
	m_mgtClient->addCategory(defConfig, true);

	// Add this service under 'North' parent category
	vector<string> children;
	children.push_back(current_name);
	m_mgtClient->addChildCategories(parent_name, children);

	// Adds sub categories to the configuration
	bool extracted = true;
	ConfigCategory subCategory;
	while (extracted) {

		extracted = subCategory.extractSubcategory(defConfigCategoryOnly);

		if (extracted) {
			DefaultConfigCategory defSubCategory(subCategory);

			createConfigCategories(defSubCategory, current_name, subCategory.getName());

			// Cleans the category
			subCategory.removeItems();
			subCategory = ConfigCategory() ;
		}
	}

}

/**
 * Load the configured north plugin
 */
bool NorthService::loadPlugin()
{
	try {
		PluginManager *manager = PluginManager::getInstance();

		if (! m_config.itemExists("plugin"))
		{
			logger->error("Unable to fetch plugin name from configuration.\n");
			return false;
		}
		m_pluginName = m_config.getValue("plugin");
		logger->info("Loading north plugin %s.", m_pluginName.c_str());
		PLUGIN_HANDLE handle;
		if ((handle = manager->loadPlugin(m_pluginName, PLUGIN_TYPE_NORTH)) != NULL)
		{
			// Adds categories and sub categories to the configuration
			DefaultConfigCategory defConfig(m_name, manager->getInfo(handle)->config);
			createConfigCategories(defConfig, string("North"), m_name);

			// Must now reload the configuration to obtain any items added from
			// the plugin
			// Removes all the m_items already present in the category
			m_config.removeItems();
			m_config = m_mgtClient->getCategory(m_name);

			try {
				northPlugin = new NorthPlugin(handle, m_config);
			} catch (...) {
				return false;
			}

			// Deal with registering and fetching the advanced configuration
			string advancedCatName = m_name+string("Advanced");
			DefaultConfigCategory defConfigAdvanced(advancedCatName, string("{}"));
			addConfigDefaults(defConfigAdvanced);
			defConfigAdvanced.setDescription(m_name+string(" advanced config params"));

			// Create/Update category name (we pass keep_original_items=true)
			m_mgtClient->addCategory(defConfigAdvanced, true);

			// Add this service under 'm_name' parent category
			vector<string> children1;
			children1.push_back(advancedCatName);
			m_mgtClient->addChildCategories(m_name, children1);

			// Must now reload the merged configuration
			m_configAdvanced = m_mgtClient->getCategory(advancedCatName);
			if (m_configAdvanced.itemExists("logLevel"))
			{
				string prevLogLevel = logger->getMinLevel();
				logger->setMinLevel(m_configAdvanced.getValue("logLevel"));

				PluginManager *manager = PluginManager::getInstance();
				PLUGIN_TYPE type = manager->getPluginImplType(northPlugin->getHandle());
				logger->debug("%s:%d: North plugin type = %s", __FUNCTION__, __LINE__, (type==PYTHON_PLUGIN)?"PYTHON_PLUGIN":"BINARY_PLUGIN");

				if (m_dataLoad)
				{
					logger->debug("%s:%d: calling m_dataLoad->configChange() for updating loglevel", __FUNCTION__, __LINE__);
					m_dataLoad->configChange("north filters", "logLevel");
				}
				
				if (type == PYTHON_PLUGIN)
				{
					// propagate loglevel changes to python filters/plugins, if present
					logger->debug("prevLogLevel=%s, m_configAdvanced.getValue(\"logLevel\")=%s", prevLogLevel.c_str(), m_configAdvanced.getValue("logLevel").c_str());
					if (prevLogLevel.compare(m_configAdvanced.getValue("logLevel")) != 0)
					{
						logger->debug("calling northPlugin->reconfigure() for updating loglevel");
						northPlugin->reconfigure("logLevel");
					}
				}
			}
			if (m_configAdvanced.itemExists("control"))
			{
				string c = m_configAdvanced.getValue("control");
				if (c.compare("true") == 0)
				{
					m_allowControl = true;
					logger->warn("Control operations have been enabled");
				}
				else
				{
					m_allowControl = false;
					logger->warn("Control operations have been disabled");
				}
			}


			return true;
		}
	} catch (exception &e) {
		logger->fatal("Failed to load north plugin: %s\n", e.what());
	}
	return false;
}

/**
 * Shutdown request
 */
void NorthService::shutdown()
{
	/* Stop recieving new requests and allow existing
	 * requests to drain.
	 */
	m_shutdown = true;
	logger->info("North service shutdown in progress.");

	// Signal main thread to shutdown
	m_cv.notify_all();
}

/**
 * Restart request
 */
void NorthService::restart()
{
	logger->info("North service restart in progress.");

	// Set restart action
	m_requestRestart = true;

	// Set shutdown action
	m_shutdown = true;

	// Signal main thread to shutdown
	m_cv.notify_all();
}

/**
 * Configuration change notification
 */
void NorthService::configChange(const string& categoryName, const string& category)
{
	logger->info("Configuration change in category %s: %s", categoryName.c_str(),
			category.c_str());
	if (categoryName.compare(m_name) == 0)
	{

		m_config = ConfigCategory(m_name, category);

		m_restartPlugin = true;
		m_cv.notify_all();

		if (m_dataLoad)
		{
			m_dataLoad->configChange(categoryName, category);
		}
	}
	if (categoryName.compare(m_name+"Advanced") == 0)
	{
		m_configAdvanced = ConfigCategory(m_name+"Advanced", category);
		if (m_configAdvanced.itemExists("logLevel"))
		{
			string prevLogLevel = logger->getMinLevel();
			logger->setMinLevel(m_configAdvanced.getValue("logLevel"));

			PluginManager *manager = PluginManager::getInstance();
			PLUGIN_TYPE type = manager->getPluginImplType(northPlugin->getHandle());
			logger->debug("%s:%d: North plugin type = %s", __FUNCTION__, __LINE__, (type==PYTHON_PLUGIN)?"PYTHON_PLUGIN":"BINARY_PLUGIN");
			
			if (m_dataLoad)
			{
				logger->debug("%s:%d: calling m_dataLoad->configChange() for updating loglevel", __FUNCTION__, __LINE__);
				m_dataLoad->configChange("north filters", "logLevel");
			}
			
			if (type == PYTHON_PLUGIN)
			{
				// propagate loglevel changes to python filters/plugins, if present
				logger->debug("prevLogLevel=%s, m_configAdvanced.getValue(\"logLevel\")=%s", prevLogLevel.c_str(), m_configAdvanced.getValue("logLevel").c_str());
				if (prevLogLevel.compare(m_configAdvanced.getValue("logLevel")) != 0)
				{
					logger->debug("%s:%d: calling northPlugin->reconfigure() for updating loglevel", __FUNCTION__, __LINE__);
					northPlugin->reconfigure("logLevel");
				}
			}
		}
		if (m_configAdvanced.itemExists("control"))
		{
			string c = m_configAdvanced.getValue("control");
			if (c.compare("true") == 0)
			{
				m_allowControl = true;
				logger->warn("Control operations have been enabled");
			}
			else
			{
				m_allowControl = false;
				logger->warn("Control operations have been disabled");
			}
		}
		if (m_configAdvanced.itemExists("blockSize"))
		{
			unsigned long newBlock = strtoul(
					m_configAdvanced.getValue("blockSize").c_str(),
					NULL,
					10);
			if (newBlock > 0)
			{
				m_dataLoad->setBlockSize(newBlock);
			}
		}
		if (m_configAdvanced.itemExists("assetTrackerInterval"))
		{
			unsigned long interval  = strtoul(
						m_configAdvanced.getValue("assetTrackerInterval").c_str(),
						NULL,
						10);
			if (m_assetTracker)
				m_assetTracker->tune(interval);
		}
		if (m_configAdvanced.itemExists("perfmon"))
		{
			string perf = m_configAdvanced.getValue("perfmon");
			if (perf.compare("true") == 0)
				m_perfMonitor->setCollecting(true);
			else
				m_perfMonitor->setCollecting(false);
		}
	}

	// Update the  Security category
	if (categoryName.compare(m_name+"Security") == 0)
	{
		this->updateSecurityCategory(category);
	}
}

/**
 * Restart the plugin with an updated configuration.
 * We need to do this as north plugins do not have a reconfigure method
 *
 * We need to make sure we are not sending data and the send data thread does not startup
 * whilst we are doing the restart.
 *
 * We also need to make sure the send data thread gets the new plugin.
 */
void NorthService::restartPlugin()
{
	m_restartPlugin = false;

	// Stop the send data thread
	m_dataSender->pause();

	if (m_pluginData)
	{
		string saveData = northPlugin->shutdownSaveData();
		string key = m_name + m_pluginName;
		logger->debug("Persist plugin data key %s is %s", key.c_str(), saveData.c_str());
		if (!m_pluginData->persistPluginData(key, saveData))
		{
			Logger::getLogger()->error("Plugin %s has failed to save data [%s] for key %s",
				m_pluginName.c_str(), saveData.c_str(), key.c_str());
		}
	}
	else
	{
		northPlugin->shutdown();
	}

	delete northPlugin;
	northPlugin = NULL;
	loadPlugin();
	// Deal with persisted data and start the plugin
	if (northPlugin->persistData())
	{
		logger->debug("Plugin %s requires persisted data", m_pluginName.c_str());
		m_pluginData = new PluginData(m_storage);
		string key = m_name + m_pluginName;
		string storedData = m_pluginData->loadStoredData(key);
		logger->debug("Starting plugin with storedData: %s", storedData.c_str());
		northPlugin->startData(storedData);
	}
	else
	{
		logger->debug("Start %s plugin", m_pluginName.c_str());
		northPlugin->start();
	}
	m_dataSender->updatePlugin(northPlugin);
	m_dataSender->release();

	// If the plugin supports control register the callback functions
	if (northPlugin->hasControl() && m_allowControl)
	{
		northPlugin->pluginRegister(controlWrite, controlOperation);
	}
}

/**
 * Add the generic north service configuration options to the advanced
 * category
 *
 * @param defaultConfiguration	The default configuration from the plugin
 */
void NorthService::addConfigDefaults(DefaultConfigCategory& defaultConfig)
{
	for (int i = 0; defaults[i].name; i++)
	{
		defaultConfig.addItem(defaults[i].name, defaults[i].description,
			defaults[i].type, defaults[i].value, defaults[i].value);
		defaultConfig.setItemDisplayName(defaults[i].name, defaults[i].displayName);
	}
	if (northPlugin->hasControl())
	{
		defaultConfig.addItem("control", "Allow write and control operations from the upstream system",
			"boolean", "true", "true");
		defaultConfig.setItemDisplayName("control", "Allow Control");
	}

	/* Add the set of logging levels to the service */
	vector<string>	logLevels = { "error", "warning", "info", "debug" };
	defaultConfig.addItem("logLevel", "Minimum logging level reported",
			"warning", "warning", logLevels);
	defaultConfig.setItemDisplayName("logLevel", "Minimum Log Level");

	// Add blockSize configuration item
	defaultConfig.addItem("blockSize",
		"The size of a block of data to send in each transmission.",
		"integer",
		std::to_string(DEFAULT_BLOCK_SIZE),
		std::to_string(DEFAULT_BLOCK_SIZE));
	defaultConfig.setItemDisplayName("blockSize", "Data block size");
	defaultConfig.addItem("assetTrackerInterval",
			"Number of milliseconds between updates of the asset tracker information",
			"integer", std::to_string(MIN_ASSET_TRACKER_UPDATE),
			std::to_string(MIN_ASSET_TRACKER_UPDATE));
	defaultConfig.setItemDisplayName("assetTrackerInterval",
			"Asset Tracker Update");
	defaultConfig.addItem("perfmon", "Track and store performance counters",
			"boolean", "false", "false");
	defaultConfig.setItemDisplayName("perfmon", "Performance Counters");
}

/**
 * Control write operation
 *
 * @param name		Name of the variable to write
 * @param value		Value to write to the variable
 * @param destination	Where to write the value
 * @return true if write was succesfully sent to dispatcher, else false
 */
bool NorthService::write(const string& name, const string& value, const ControlDestination destination)
{
	Logger::getLogger()->info("Control write %s with %s", name.c_str(), value.c_str());
	if (destination != DestinationBroadcast)
	{
		Logger::getLogger()->error("Write destination requires an argument that is not given");
		return -1;
	}
	// Build payload for dispatcher service
	string payload = "{ \"destination\" : \"broadcast\",";
	payload += controlSource();
	payload += ", \"write\" : { \"";
	payload += name;
	payload += "\" : \"";
	string escaped = value;
	StringEscapeQuotes(escaped);
	payload += escaped;
	payload += "\" } }";
	return sendToDispatcher("/dispatch/write", payload);
}

/**
 * Control write operation
 *
 * @param name		Name of the variable to write
 * @param value		Value to write to the variable
 * @param destination	Where to write the value
 * @param arg		Argument used to determine destination
 * @return true if write was succesfully sent to dispatcher, else false
 */
bool NorthService::write(const string& name, const string& value, const ControlDestination destination, const string& arg)
{
	Logger::getLogger()->info("Control write %s with %s", name.c_str(), value.c_str());

	// Build payload for dispatcher service
	string payload = "{ \"destination\" : \"";
	switch (destination)
	{
		case DestinationService:
			payload += "service\", \"name\" : \"";
			payload += arg;
			payload += "\"";
			break;
		case DestinationAsset:
			payload += "asset\", \"name\" : \"";
			payload += arg;
			payload += "\"";
			break;
		case DestinationScript:
			payload += "script\", \"name\" : \"";
			payload += arg;
			payload += "\"";
			break;
		case DestinationBroadcast:
			payload += "broadcast\"";
			break;
	}
	payload += ", ";
	payload += controlSource();
	payload += ", \"write\" : { \"";
	payload += name;
	payload += "\" : \"";
	string escaped = value;
	StringEscapeQuotes(escaped);
	payload += escaped;
	payload += "\" } }";
	return sendToDispatcher("/dispatch/write", payload);
}

/**
 * Control operation
 *
 * @param name		Name of the operation to perform
 * @param paramCount	The number of parameters
 * @param parameters	The parameters to the operation
 * @param destination	Where to write the value
 * @return -1 in case of error on operation destination, 1 if operation was succesfully sent to dispatcher, else 0
 */
int  NorthService::operation(const string& name, int paramCount, char *names[], char *parameters[], const ControlDestination destination)
{
	Logger::getLogger()->info("Control operation %s with %d parameters", name.c_str(),
			paramCount);
	for (int i = 0; i < paramCount; i++)
		Logger::getLogger()->info("Parameter %d: %s", i, parameters[i]);
	if (destination != DestinationBroadcast)
	{
		Logger::getLogger()->error("Operation destination requires an argument that is not given");
		return -1;
	}
	// Build payload for dispatcher service
	string payload = "{ \"destination\" : \"broadcast\",";
	payload += controlSource();
	payload += ", \"operation\" : { \"";
	payload += name;
	payload += "\" : { ";
	for (int i = 0; i < paramCount; i++)
	{
		payload += "\"";
		payload += names[i];
		payload += "\": \"";
		string escaped = parameters[i];
		StringEscapeQuotes(escaped);
		payload += escaped;
		payload += "\"";
		if (i < paramCount -1)
			payload += ",";
	}
	payload += " } } }";
	return static_cast<int>(sendToDispatcher("/dispatch/operation", payload));
}

/**
 * Control write operation
 *
 * @param name		Name of the operation to perform
 * @param paramCount	The number of parameters
 * @param parameters	The parameters to the operation
 * @param destination	Where to write the value
 * @param arg		Argument used to determine destination
 * @return 1 if operation was succesfully sent to dispatcher, else 0
 */
int NorthService::operation(const string& name, int paramCount, char *names[], char *parameters[], const ControlDestination destination, const string& arg)
{
	Logger::getLogger()->info("Control operation %s with %d parameters", name.c_str(),
			paramCount);
	for (int i = 0; i < paramCount; i++)
		Logger::getLogger()->info("Parameter %d: %s", i, parameters[i]);
	// Build payload for dispatcher service
	string payload = "{ \"destination\" : \"";
	switch (destination)
	{
		case DestinationService:
			payload += "service\", \"name\" : \"";
			payload += arg;
			payload += "\"";
			break;
		case DestinationAsset:
			payload += "asset\", \"name\" : \"";
			payload += arg;
			payload += "\"";
			break;
		case DestinationScript:
			payload += "script\", \"name\" : \"";
			payload += arg;
			payload += "\"";
			break;
		case DestinationBroadcast:
			payload += "broadcast\"";
			break;
	}
	payload += ", ";
	payload += controlSource();
	payload += ", \"operation\" : { \"";
	payload += name;
	payload += "\" : { ";
	for (int i = 0; i < paramCount; i++)
	{
		payload += "\"";
		payload += names[i];
		payload += "\": \"";
		string escaped = parameters[i];
		StringEscapeQuotes(escaped);
		payload += escaped;
		payload += "\"";
		if (i < paramCount -1)
			payload += ",";
	}
	payload += "} } }";
	return static_cast<int>(sendToDispatcher("/dispatch/operation", payload));
}

/**
 * Send to a south service direct. This is temporary until we have the 
 * service dispatcher in place.
 */
bool NorthService::sendToService(const string& southService, const string& name, const string& value)
{
	std::string payload = "{ \"values\" : { \"";
	payload += name;
	payload += "\": \"";
	payload += value;
	payload += "\"} }";

	// Send the control message to the south service
	try {
		ServiceRecord service(southService);
		if (!m_mgtClient->getService(service))
		{
			Logger::getLogger()->error("Unable to find service '%s'", southService.c_str());
			return false;
		}
		string address = service.getAddress();
		unsigned short port = service.getPort();
		char addressAndPort[80];
		snprintf(addressAndPort, sizeof(addressAndPort), "%s:%d", address.c_str(), port);
		SimpleWeb::Client<SimpleWeb::HTTP> http(addressAndPort);

		string url = "/fledge/south/setpoint";
		try {
			SimpleWeb::CaseInsensitiveMultimap headers = {{"Content-Type", "application/json"}};
			auto res = http.request("PUT", url, payload, headers);
			if (res->status_code.compare("200 OK"))
			{
				Logger::getLogger()->error("Failed to send set point operation to service %s, %s",
						southService.c_str(), res->status_code.c_str());
				Logger::getLogger()->error("Failed Payload: %s", payload.c_str());
				return false;
			}
		} catch (exception& e) {
			Logger::getLogger()->error("Failed to send set point operation to service %s, %s",
						southService.c_str(), e.what());
			return false;
		}

		return true;
	}
	catch (exception &e) {
		Logger::getLogger()->error("Failed to send set point operation to service %s, %s",
				southService.c_str(), e.what());
		return false;
	}

}

/**
 * Send to the control dispatcher service
 */
bool NorthService::sendToDispatcher(const string& path, const string& payload)
{
	Logger::getLogger()->debug("Dispatch %s with %s", path.c_str(), payload.c_str());
	// Send the control message to the south service
	try {
		ServiceRecord service("dispatcher");
		if (!m_mgtClient->getService(service))
		{
			Logger::getLogger()->error("Unable to find dispatcher service 'Dispatcher'");
			return false;
		}
		string address = service.getAddress();
		unsigned short port = service.getPort();
		char addressAndPort[80];
		snprintf(addressAndPort, sizeof(addressAndPort), "%s:%d", address.c_str(), port);
		SimpleWeb::Client<SimpleWeb::HTTP> http(addressAndPort);

		try {
			SimpleWeb::CaseInsensitiveMultimap headers = {{"Content-Type", "application/json"}};
			// Pass North service bearer token to dispatcher
			string regToken = m_mgtClient->getRegistrationBearerToken();
			if (regToken != "")
			{
				headers.emplace("Authorization", "Bearer " + regToken);
			}

			auto res = http.request("POST", path, payload, headers);
			if (res->status_code.compare("202 Accepted"))
			{
				Logger::getLogger()->error(
						"Failed to send control operation '%s' to dispatcher service, %s %s",
							path.c_str(), res->status_code.c_str(),
							res->content.string().c_str());
				Logger::getLogger()->error("Failed Payload: %s", payload.c_str());
				return false;
			}
		} catch (exception& e) {
			Logger::getLogger()->error("Failed to send control operation to dispatcher service, %s",
						e.what());
			return false;
		}

		return true;
	}
	catch (exception &e) {
		Logger::getLogger()->error("Failed to send control operation to dispatcher service, %s", e.what());
		return false;
	}

}

/**
 * Return the control source for control operations. This is used
 * for pipeline matching.
 *
 * @return string	The control source
 */
string NorthService::controlSource()
{
	string source = "\"source\" : \"service\", \"source_name\" : \"";
	source += m_name;
	source += "\"";

	return source;
}

/*
 * Fledge north service.
 *
 * Copyright (c) 2020 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
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

/**
 * North service main entry point
 */
int main(int argc, char *argv[])
{
unsigned short corePort = 8082;
string	       coreAddress = "localhost";
bool	       daemonMode = true;
string	       myName = SERVICE_NAME;
string	       logLevel = "warning";

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
	}

	if (daemonMode && makeDaemon() == -1)
	{
		// Failed to run in daemon mode
		cout << "Failed to run as deamon - proceeding in interactive mode." << endl;
	}

	NorthService *service = new NorthService(myName);
	Logger::getLogger()->setMinLevel(logLevel);
	service->start(coreAddress, corePort);
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
	(void)open("/dev/null", O_RDWR);  	// stdin
	(void)dup(0);  			// stdout	GCC bug 66425 produces warning
	(void)dup(0);  			// stderr	GCC bug 66425 produces warning
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
NorthService::NorthService(const string& myName) : m_name(myName), m_shutdown(false), m_storage(NULL)
{
	logger = new Logger(myName);
	logger->setMinLevel("warning");
}

/**
 * Destructor for the north service
 */
NorthService::~NorthService()
{
	if (m_storage)
		delete m_storage;
}

ManagementClient *NorthService::m_mgtClient = NULL;

ManagementClient *NorthService::getMgmtClient()
{
	return m_mgtClient;
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
		ServiceRecord record(m_name, "Northbound", "http", "localhost", 0, managementListener);
		m_mgtClient = new ManagementClient(coreAddress, corePort);

		// Create an empty North category if one doesn't exist
		DefaultConfigCategory northConfig(string("North"), string("{}"));
		northConfig.setDescription("North");
		m_mgtClient->addCategory(northConfig, true);

		m_config = m_mgtClient->getCategory(m_name);
		if (!loadPlugin())
		{
			logger->fatal("Failed to load north plugin, exiting...");
			management.stop();
			return;
		}
		if (!m_mgtClient->registerService(record))
		{
			logger->error("Failed to register service %s", m_name.c_str());
		}
		ConfigHandler *configHandler = ConfigHandler::getInstance(m_mgtClient);
		configHandler->registerCategory(this, m_name);
		configHandler->registerCategory(this, m_name+"Advanced");

		// Get a handle on the storage layer
		ServiceRecord storageRecord("Fledge Storage");
		if (!m_mgtClient->getService(storageRecord))
		{
			logger->fatal("Unable to find storage service");
			return;
		}
		logger->info("Connect to storage on %s:%d",
				storageRecord.getAddress().c_str(),
				storageRecord.getPort());

		
		m_storage = new StorageClient(storageRecord.getAddress(),
						storageRecord.getPort());

		// Fetch Confguration
		m_assetTracker = new AssetTracker(m_mgtClient, m_name);
		AssetTracker::getAssetTracker()->populateAssetTrackingCache(m_name, "Egress");

		// Setup the data loading
		long streamId = 0;
		if (m_config.itemExists("streamId"))
		{
			streamId = strtol(m_config.getValue("streamId").c_str(), NULL, 10);
		}
		m_dataLoad = new DataLoad(m_name, streamId, m_storage);
		if (m_config.itemExists("source"))
		{
			m_dataLoad->setDataSource(m_config.getValue("source"));
		}
		m_dataSender = new DataSender(northPlugin, m_dataLoad, this);

		
		// wait for shutdown
		unique_lock<mutex> lck(m_mutex);
		while (!m_shutdown)
		{
			m_cv.wait(lck);
		}

		delete m_dataLoad;
		delete m_dataSender;


		// Shutdown the north plugin
		if (northPlugin)
			northPlugin->shutdown();
		
		// Clean shutdown, unregister the storage service
		m_mgtClient->unregisterService();
	}
	management.stop();
	logger->info("North service shutdown completed");
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
	defConfig.setDescription(current_name);	// TODO We do not have access to the description

	DefaultConfigCategory defConfigCategoryOnly(defConfig);
	defConfigCategoryOnly.keepItemsType(ConfigCategory::ItemType::CategoryType);
	defConfig.removeItemsType(ConfigCategory::ItemType::CategoryType);

	DefaultConfigCategory serviceConfig(current_name,
                                               defaultServiceConfig);
	defConfig += serviceConfig;

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

			try {
				northPlugin = new NorthPlugin(handle, m_config);
			} catch (...) {
				return false;
			}

			return true;
		}
	} catch (exception e) {
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
	unique_lock<mutex> lck(m_mutex);
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
		try {
			northPlugin->reconfigure(category);
		}
		catch (...) {
			logger->fatal("Unrecoverable failure during North plugin reconfigure, north service exiting...");
			shutdown();
		}
	}
	if (categoryName.compare(m_name+"Advanced") == 0)
	{
		m_configAdvanced = ConfigCategory(m_name+"Advanced", category);
		if (m_configAdvanced.itemExists("logLevel"))
		{
			logger->setMinLevel(m_configAdvanced.getValue("logLevel"));
		}
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

	/* Add the set of logging levels to the service */
	vector<string>	logLevels = { "error", "warning", "info", "debug" };
	defaultConfig.addItem("logLevel", "Minimum logging level reported",
			"warning", "warning", logLevels);
	defaultConfig.setItemDisplayName("logLevel", "Minimum Log Level");
}


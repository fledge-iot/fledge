/*
 * Fledge south service.
 *
 * Copyright (c) 2018 OSisoft, LLC
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
#include <south_service.h>
#include <south_api.h>
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
#include <config_handler.h>
#include <syslog.h>
#include <pyruntime.h>

#define SERVICE_TYPE "Southbound"

extern int makeDaemon(void);
extern void handler(int sig);

static void reconfThreadMain(void *arg);

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
string	       logLevel = "warning";
string         token = "";
bool	       dryrun = false;

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
			dryrun = true;
		}
	}

	if (daemonMode && makeDaemon() == -1)
	{
		// Failed to run in daemon mode
		cout << "Failed to run as deamon - proceeding in interactive mode." << endl;
	}

	SouthService *service = new SouthService(myName, token);
	if (dryrun)
	{
		service->setDryRun();
	}
	Logger *logger = Logger::getLogger();
	logger->setMinLevel(logLevel);
	// Start the service. This will oly return whren the serivce is shutdown
	service->start(coreAddress, corePort);
	delete service;
	delete logger;
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
	if (dup(0) == -1) {}			// stdout	Workaround for GCC bug 66425 produces warning
	if (dup(0) == -1) {} 			// stderr	WOrkaround for GCC bug 66425 produces warning
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
 * Callback called by south plugin to ingest readings into Fledge
 *
 * @param ingest	The ingest class to use
 * @param reading	The Reading to ingest
 */
void doIngest(Ingest *ingest, Reading reading)
{
	ingest->ingest(reading);
}

void doIngestV2(Ingest *ingest, ReadingSet *set)
{
    std::vector<Reading *> *vec = set->getAllReadingsPtr();
    if (!vec)
    {
        Logger::getLogger()->info("%s:%d: V2 async ingest method: vec is NULL", __FUNCTION__, __LINE__);
        return;
    }
	// move reading vector from set to new vector vec2
    std::vector<Reading *> *vec2 = set->moveAllReadings();
    
    Logger::getLogger()->debug("%s:%d: V2 async ingest method returned: vec->size()=%d", __FUNCTION__, __LINE__, vec->size());

	ingest->ingest(vec2);
	delete vec2; 	// each reading object inside vector has been allocated on heap and moved to Ingest class's internal queue
	delete set;

	ingest->flowControl();
}

/**
 * Constructor for the south service
 */
SouthService::SouthService(const string& myName, const string& token) :
				southPlugin(NULL),
				m_assetTracker(NULL),
				m_shutdown(false),
				m_readingsPerSec(1),
				m_throttle(false),
				m_throttled(false),
				m_token(token),
				m_repeatCnt(1),
				m_pluginData(NULL),
				m_dryRun(false),
				m_requestRestart(false),
				m_auditLogger(NULL),
				m_perfMonitor(NULL)
{
	m_name = myName;
	m_type = SERVICE_TYPE;
	m_pollType = POLL_INTERVAL;

	logger = new Logger(myName);
	logger->setMinLevel("warning");

	m_reconfThread = new std::thread(reconfThreadMain, this);
}

/**
 * Destructor for south service
 */
SouthService::~SouthService()
{
	m_cvNewReconf.notify_all();	// Wakeup the reconfigure thread to terminate it
	m_reconfThread->join();
	delete m_reconfThread;
	if (m_pluginData)
		delete m_pluginData;
	if (m_perfMonitor)
		delete m_perfMonitor;
	delete m_assetTracker;
	delete m_auditLogger;
	delete m_mgtClient;

	// We would like to shutdown the Python environment if it
	// was running. However this causes a segmentation fault within Python
	// so we currently can not do this
#if PYTHON_SHUTDOWN
	PythonRuntime::shutdown();	// Shutdown and release Python resources
#endif
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

	// Create the south API
	SouthApi *api = new SouthApi(this);
	if (!api)
	{
		logger->fatal("Unable to create API object");
		return;
	}
	// Allow time for the listeners to start before we register
	sleep(1);
	if (! m_shutdown)
	{
		unsigned short sport = api->getListenerPort();

		// Now register our service
		// TODO proper hostname lookup
		unsigned short managementListener = management.getListenerPort();
		ServiceRecord record(m_name,			// Service name
					SERVICE_TYPE,		// Service type
					"http",			// Protocol
					"localhost",		// Listening address
					sport,			// Service port
					managementListener,	// Management port
					m_token);		// Token

		// Allocate and save ManagementClient object
		m_mgtClient = new ManagementClient(coreAddress, corePort);

		// Create the audit logger instance
		m_auditLogger = new AuditLogger(m_mgtClient);

		// Create an empty South category if one doesn't exist
		DefaultConfigCategory southConfig(string("South"), string("{}"));
		southConfig.setDescription("South");
		m_mgtClient->addCategory(southConfig, true);

		// Get configuration for service name
		m_config = m_mgtClient->getCategory(m_name);
		if (!loadPlugin())
		{
			logger->fatal("Failed to load south plugin, exiting...");
			management.stop();
			return;
		}

		if (southPlugin->hasControl())
		{
			logger->info("South plugin has a control facility, adding south service API");
		}

		if (!m_dryRun)
		{
			if (!m_mgtClient->registerService(record))
			{
				logger->error("Failed to register service %s", m_name.c_str());
				management.stop();
				return;
			}

			// Register for category content changes
			ConfigHandler *configHandler = ConfigHandler::getInstance(m_mgtClient);
			configHandler->registerCategory(this, m_name);
			configHandler->registerCategory(this, m_name+"Advanced");
		}

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

		
		StorageClient storage(storageRecord.getAddress(),
						storageRecord.getPort());
		storage.registerManagement(m_mgtClient);

		m_perfMonitor = new PerformanceMonitor(m_name, &storage);
		unsigned int threshold = 100;
		long timeout = 5000;
		std::string pluginName;
		try {
			if (m_configAdvanced.itemExists("bufferThreshold"))
				threshold = (unsigned int)strtol(m_configAdvanced.getValue("bufferThreshold").c_str(), NULL, 10);
			if (m_configAdvanced.itemExists("maxSendLatency"))
				timeout = strtol(m_configAdvanced.getValue("maxSendLatency").c_str(), NULL, 10);
			if (m_config.itemExists("plugin"))
				pluginName = m_config.getValue("plugin");
			if (m_configAdvanced.itemExists("logLevel"))
			{
				string prevLogLevel = logger->getMinLevel();
				logger->setMinLevel(m_configAdvanced.getValue("logLevel"));

				PluginManager *manager = PluginManager::getInstance();
				PLUGIN_TYPE type = manager->getPluginImplType(southPlugin->getHandle());
				logger->debug("%s:%d: plugin type = %s", __FUNCTION__, __LINE__, (type==PYTHON_PLUGIN)?"PYTHON_PLUGIN":"BINARY_PLUGIN");
				
				if (type == PYTHON_PLUGIN)
				{
					// propagate loglevel changes to python filters/plugins, if present
					logger->debug("prevLogLevel=%s, m_configAdvanced.getValue(\"logLevel\")=%s", prevLogLevel.c_str(), m_configAdvanced.getValue("logLevel").c_str());
					if (prevLogLevel.compare(m_configAdvanced.getValue("logLevel")) != 0)
					{
						logger->debug("calling southPlugin->reconfigure() for updating loglevel");
						southPlugin->reconfigure("logLevel");
					}
				}
			}
			if (m_configAdvanced.itemExists("throttle"))
			{
				string throt = m_configAdvanced.getValue("throttle");
				if (throt[0] == 't' || throt[0] == 'T')
				{
					m_throttle = true;
					m_highWater = threshold
					       	+ (((float)threshold * SOUTH_THROTTLE_HIGH_PERCENT) / 100.0);
					m_lowWater = threshold
					       	+ (((float)threshold * SOUTH_THROTTLE_LOW_PERCENT) / 100.0);
					logger->info("Throttling is enabled, high water mark is set to %ld", m_highWater);
				}
				else
				{
					m_throttle = false;
				}
			}
		} catch (ConfigItemNotFound e) {
			logger->info("Defaulting to inline defaults for south configuration");
		}

		m_assetTracker = new AssetTracker(m_mgtClient, m_name);
		if (m_configAdvanced.itemExists("assetTrackerInterval"))
		{
			string interval = m_configAdvanced.getValue("assetTrackerInterval");
			unsigned long i = strtoul(interval.c_str(), NULL, 10);
			if (m_assetTracker)
				m_assetTracker->tune(i);
		}

		{
		// Instantiate the Ingest class
		Ingest ingest(storage, m_name, pluginName, m_mgtClient);
		ingest.setPerfMon(m_perfMonitor);
		m_ingest = &ingest;
		if (m_throttle)
		{
			m_ingest->setFlowControl(m_lowWater, m_highWater);
		}

		if (m_configAdvanced.itemExists("statistics"))
		{
			m_ingest->setStatistics(m_configAdvanced.getValue("statistics"));
		}

		if (m_configAdvanced.itemExists("perfmon"))
		{
			string perf = m_configAdvanced.getValue("perfmon");
			if (perf.compare("true") == 0)
				m_perfMonitor->setCollecting(true);
			else
				m_perfMonitor->setCollecting(false);
		}

		m_ingest->start(timeout, threshold);	// Start the ingest threads running

		try {
			m_readingsPerSec = 1;
			if (m_configAdvanced.itemExists("readingsPerSec"))
				m_readingsPerSec = (unsigned long)strtol(m_configAdvanced.getValue("readingsPerSec").c_str(), NULL, 10);
			if (m_readingsPerSec < 1)
			{
				logger->warn("Invalid setting of reading rate, defaulting to 1");
				m_readingsPerSec = 1;
			}
		} catch (ConfigItemNotFound e) {
			logger->info("Defaulting to inline default for poll interval");
		}

		// Load filter plugins and set them in the Ingest class
		if (!ingest.loadFilters(m_name))
		{
			string errMsg("'" + m_name + "' plugin: failed loading filter plugins.");
			Logger::getLogger()->fatal((errMsg + " Exiting.").c_str());
			throw runtime_error(errMsg);
		}

		if (southPlugin->persistData())
		{
			m_pluginData = new PluginData(new StorageClient(storageRecord.getAddress(),
                                                storageRecord.getPort()));
			m_dataKey = m_name + m_config.getValue("plugin");
		}

		// Create default security category
		this->createSecurityCategories(m_mgtClient, m_dryRun);

		if (!m_dryRun)	// If not a dry run then handle readings
		{
			// Get and ingest data
			if (! southPlugin->isAsync())
			{
				calculateTimerRate();
				m_timerfd = createTimerFd(m_desiredRate); // interval to be passed is in usecs
				m_currentRate = m_desiredRate;
				if (m_timerfd < 0)
				{
					logger->fatal("Could not create timer FD");
					return;
				}
				
				int pollCount = 0;
				struct timespec start, end;
				if (clock_gettime(CLOCK_MONOTONIC, &start) == -1)
				   Logger::getLogger()->error("polling loop start: clock_gettime");

				const char *pluginInterfaceVer = southPlugin->getInfo()->interface;
				bool pollInterfaceV2 = (pluginInterfaceVer[0]=='2' && pluginInterfaceVer[1]=='.');
				logger->info("pollInterfaceV2=%s", pollInterfaceV2?"true":"false");

				/*
				 * Start the plugin. If it fails with an exception, retry the start with a delay
				 * That delay starts at 500mS and will backoff to 1 minute
				 *
				 * We will continue to retry the start until the service is shutdown
				 */
				bool started = false;
				int delay = 500;
				while (started == false && m_shutdown == false)
				{
					if (southPlugin->persistData())
					{
						Logger::getLogger()->debug("Plugin persists data");
						string pluginData = m_pluginData->loadStoredData(m_dataKey);
						try {
							southPlugin->startData(pluginData);
							started = true;
						} catch (...) {
							Logger::getLogger()->debug("Plugin start raised an exception");
						}
					}
					else
					{
						Logger::getLogger()->debug("Plugin does not persist data");
						started = true;
					}
					if (!started)
					{
						std::this_thread::sleep_for(std::chrono::milliseconds(delay));
						if (delay < 60 * 1000)	// Backoff the delay to 1 minute
						{
							delay *= 2;
						}
					}
				}

				while (!m_shutdown)
				{
					uint64_t exp = 0;
					ssize_t s;
					
					if (m_pollType == POLL_FIXED)
					{
						if (syncToNextPoll())
							exp = 1;	// Perform one poll
					}
					else if (m_pollType == POLL_INTERVAL)
					{
						long rep = m_repeatCnt;
						while (rep > 0)
						{
							s = read(m_timerfd, &exp, sizeof(uint64_t));
							if ((unsigned int)s != sizeof(uint64_t))
								logger->error("timerfd read()");
							if (exp > 100 && exp > m_readingsPerSec/2)
							logger->error("%d expiry notifications accumulated", exp);
							rep--;
							if (m_shutdown)
							{
								break;
							}
							checkPendingReconfigure();
							if (rep > m_repeatCnt)
							{
								// Reconfigure has resulted in more frequent
								// polling
								rep = m_repeatCnt;
							}
						}
					}
					else if (m_pollType == POLL_ON_DEMAND)
					{
						if (onDemandPoll())
							exp = 1;
					}
					if (m_shutdown)
					{
						break;
					}
#if DO_CATCHUP
					for (uint64_t i=0; i<exp; i++)
#endif
					{
						if (!pollInterfaceV2) // v1 poll method
						{
						
							Reading reading = southPlugin->poll();
							if (reading.getDatapointCount())
							{
								ingest.ingest(reading);
							}
							++pollCount;
						}
						else // V2 poll method
						{
							checkPendingReconfigure();
							ReadingSet *set = southPlugin->pollV2();
							if (set)
							{
							    std::vector<Reading *> *vec = set->getAllReadingsPtr();
							    if (!vec)
							    {
								Logger::getLogger()->info("%s:%d: V2 poll method: vec is NULL", __FUNCTION__, __LINE__);
								continue;
							    }
							    // move reading vector from set to vec2
								std::vector<Reading *> *vec2 = set->moveAllReadings();
								ingest.ingest(vec2);
								pollCount += (int) vec2->size();
								delete vec2; 	// each reading object inside vector has been allocated on heap and moved to Ingest class's internal queue
								delete set;
							}
						}
						throttlePoll();
					}
				}
				if (clock_gettime(CLOCK_MONOTONIC, &end) == -1)
				   Logger::getLogger()->error("polling loop end: clock_gettime");
				
				int secs = end.tv_sec - start.tv_sec;
				int nsecs = end.tv_nsec - start.tv_nsec;
				if (nsecs < 0)
				{
					secs--;
					nsecs += 1000000000;
				}
				Logger::getLogger()->info("%d readings generated in %d.%d secs", pollCount, secs, nsecs);
				close(m_timerfd);
			}
			else
			{
				const char *pluginInterfaceVer = southPlugin->getInfo()->interface;
				bool pollInterfaceV2 = (pluginInterfaceVer[0]=='2' && pluginInterfaceVer[1]=='.');
				Logger::getLogger()->info("pluginInterfaceVer=%s, pollInterfaceV2=%s", pluginInterfaceVer, pollInterfaceV2?"true":"false");
				if (!pollInterfaceV2)
					southPlugin->registerIngest((INGEST_CB)doIngest, &ingest);
				else
					southPlugin->registerIngestV2((INGEST_CB2)doIngestV2, &ingest);
				bool started = false;
				int backoff = 1000;
				while (started == false && m_shutdown == false)
				{
					try {
						if (southPlugin->persistData())
						{
							string pluginData = m_pluginData->loadStoredData(m_dataKey);
							Logger::getLogger()->debug("Plugin persists data, %s", pluginData.c_str());
							southPlugin->startData(pluginData);
						}
						else
						{
							Logger::getLogger()->debug("Plugin does not persist data");
							southPlugin->start();
						}
						started = true;
					} catch (...) {
						Logger::getLogger()->debug("Plugin start raised an exception");
						std::this_thread::sleep_for(std::chrono::milliseconds(backoff));
						if (backoff < 60000)
						{
							backoff *= 2;
						}
					}
				}
				while (!m_shutdown)
				{
					std::this_thread::sleep_for(std::chrono::milliseconds(1000));
				}
			}
		}
		else
		{
			m_shutdown = true;
			Logger::getLogger()->info("Dryrun of service, shutting down");
		}

		// Shutdown the API
		delete api;

		// do plugin shutdown before destroying Ingest object on stack
		if (southPlugin)
		{
			if (southPlugin->persistData())
			{
				string data = southPlugin->shutdownSaveData();
				Logger::getLogger()->debug("Persist plugin data, %s '%s'", m_dataKey, data.c_str());
				m_pluginData->persistPluginData(m_dataKey, data);
			}
			else
			{
				southPlugin->shutdown();
			}
			delete southPlugin;
			southPlugin = NULL;
		}
		}
		
		// Clean shutdown, unregister the storage service
		if (!m_dryRun)
		{
			if (m_requestRestart)
			{
				m_mgtClient->restartService();
			}
			else
			{
				m_mgtClient->unregisterService();
			}
		}
	}
	management.stop();
	logger->info("South service shutdown %s completed", m_dryRun ? "from dry run " : "");
}

/**
 * Stop the storage service/
 */
void SouthService::stop()
{

	logger->info("Stopping south service...\n");
}

/**
 * Creates config categories and sub categories recursively, along with their parent-child relations
 */
void SouthService::createConfigCategories(DefaultConfigCategory configCategory, std::string parent_name, std::string current_name)
{

	// Deal with registering and fetching the configuration
	DefaultConfigCategory defConfig(configCategory);
	defConfig.setDescription(current_name);	// TODO We do not have access to the description

	DefaultConfigCategory defConfigCategoryOnly(defConfig);
	defConfigCategoryOnly.keepItemsType(ConfigCategory::ItemType::CategoryType);
	defConfig.removeItemsType(ConfigCategory::ItemType::CategoryType);

	// Create/Update category name (we pass keep_original_items=true)
	m_mgtClient->addCategory(defConfig, true);

	// Add this service under 'South' parent category
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
			// Adds categories and sub categories to the configuration
			DefaultConfigCategory defConfig(m_name, manager->getInfo(handle)->config);
			createConfigCategories(defConfig, string("South"), m_name);

			// Must now reload the configuration to obtain any items added from
			// the plugin
			// Removes all the m_items already present in the category
			m_config.removeItems();
			m_config = m_mgtClient->getCategory(m_name);
			m_config.addItem("mgmt_client_url_base", "Management client host and port",
                             "string", "127.0.0.1:0",
                             m_mgtClient->getUrlbase());
			try {
				southPlugin = new SouthPlugin(handle, m_config);
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
	if (m_pollType == POLL_ON_DEMAND)
	{
		lock_guard<mutex> lk(m_pollMutex);
		m_shutdown = true;
		m_pollCV.notify_all();
	}
	else
	{
		m_shutdown = true;
	}
	logger->info("South service shutdown in progress.");
}

/**
 * Restart request
 */
void SouthService::restart()
{
	/* Stop recieving new requests and allow existing
	 * requests to drain.
	 */
	m_requestRestart = true;
	m_shutdown = true;
	logger->info("South service shutdown for restart in progress.");
}

/**
 * Configuration change notification
 *
 * @param categoryName	Category name
 * @param category	Category value
 */
void SouthService::processConfigChange(const string& categoryName, const string& category)
{
	logger->info("Configuration change in category %s: %s", categoryName.c_str(),
			category.c_str());
	if (categoryName.compare(m_name) == 0)
	{
		m_config = ConfigCategory(m_name, category);
		try {
			southPlugin->reconfigure(category);
		}
		catch (...) {
			logger->fatal("Unrecoverable failure during South plugin reconfigure, south service exiting...");
			shutdown();
		}
		// Let ingest class check for changes to filter pipeline
		m_ingest->configChange(categoryName, category);
	}
	if (categoryName.compare(m_name+"Advanced") == 0)
	{
		m_configAdvanced = ConfigCategory(m_name+"Advanced", category);
		if (m_configAdvanced.itemExists("statistics"))
		{
			m_ingest->setStatistics(m_configAdvanced.getValue("statistics"));
		}
		if (m_configAdvanced.itemExists("perfmon"))
		{
			string perf = m_configAdvanced.getValue("perfmon");
			if (perf.compare("true") == 0)
				m_perfMonitor->setCollecting(true);
			else
				m_perfMonitor->setCollecting(false);
		}
		if (! southPlugin->isAsync())
		{
			try {
				unsigned long newval = (unsigned long)strtol(m_configAdvanced.getValue("readingsPerSec").c_str(), NULL, 10);
				if (newval < 1)
				{
					logger->warn("Invalid setting of reading rate, defaulting to 1");
					m_readingsPerSec = 1;
				}
				string units = m_configAdvanced.getValue("units");
				string pollType = m_configAdvanced.getValue("pollType");
				bool wakeup = false;
				if (m_pollType == POLL_ON_DEMAND)
				{
					wakeup = true;
				}
				if (pollType.compare("Fixed Times") == 0)
				{
					m_pollType = POLL_FIXED;
					processNumberList(m_configAdvanced, "pollHours", m_hours);
					processNumberList(m_configAdvanced, "pollMinutes", m_minutes);
					processNumberList(m_configAdvanced, "pollSeconds", m_seconds);

					if (m_minutes.size() == 0 && m_hours.size() != 0)
						m_minutes.push_back(0);
					if (m_seconds.size() == 0 && m_minutes.size() != 0)
						m_seconds.push_back(0);

					m_desiredRate.tv_sec  = 1;
					m_desiredRate.tv_usec = 0;
					if (wakeup)
					{
						// Wakup from on demand polling
						m_pollCV.notify_all();
					}
				}
				else if (pollType.compare("Interval") == 0
						&& (newval != m_readingsPerSec || m_rateUnits.compare(units) != 0))
				{
					m_pollType = POLL_INTERVAL;
					m_readingsPerSec = newval;
					m_rateUnits = units;
					close(m_timerfd);
					calculateTimerRate();
					m_currentRate = m_desiredRate;
					m_timerfd = createTimerFd(m_desiredRate); // interval to be passed is in usecs
					if (wakeup)
					{
						// Wakup from on demand polling
						m_pollCV.notify_all();
					}
				}
				else if (pollType.compare("Interval") == 0 && m_pollType != POLL_INTERVAL)
				{
					// Change to interval mode without the rate changing
					m_pollType = POLL_INTERVAL;
					if (wakeup)
					{
						// Wakup from on demand polling
						m_pollCV.notify_all();
					}
				}
				else if (pollType.compare("On Demand") == 0)
				{
					m_pollType = POLL_ON_DEMAND;
				}
			} catch (ConfigItemNotFound e) {
				logger->error("Failed to update poll interval following configuration change");
			}
		}
		unsigned long threshold = 5000;	// This should never be used
		if (m_configAdvanced.itemExists("bufferThreshold"))
		{
			threshold = (unsigned int)strtol(m_configAdvanced.getValue("bufferThreshold").c_str(), NULL, 10);
			m_ingest->setThreshold(threshold);
		}
		if (m_configAdvanced.itemExists("maxSendLatency"))
		{
			m_ingest->setTimeout(strtol(m_configAdvanced.getValue("maxSendLatency").c_str(), NULL, 10));
		}
		if (m_configAdvanced.itemExists("logLevel"))
		{
			string prevLogLevel = logger->getMinLevel();
			logger->setMinLevel(m_configAdvanced.getValue("logLevel"));

			PluginManager *manager = PluginManager::getInstance();
			PLUGIN_TYPE type = manager->getPluginImplType(southPlugin->getHandle());
			logger->debug("%s:%d: South plugin type = %s", __FUNCTION__, __LINE__, (type==PYTHON_PLUGIN)?"PYTHON_PLUGIN":"BINARY_PLUGIN");

			// propagate loglevel change to filter irrespective whether the host plugin is python/binary
			m_ingest->configChange(categoryName, "logLevel");
			
			if (type == PYTHON_PLUGIN)
			{
				// propagate loglevel changes to python filters/plugins, if present
				logger->debug("prevLogLevel=%s, m_configAdvanced.getValue(\"logLevel\")=%s", prevLogLevel.c_str(), m_configAdvanced.getValue("logLevel").c_str());
				if (prevLogLevel.compare(m_configAdvanced.getValue("logLevel")) != 0)
				{
					logger->debug("%s:%d: calling southPlugin->reconfigure() for updating loglevel", __FUNCTION__, __LINE__);
					southPlugin->reconfigure("logLevel");
				}
			}
		}
		if (m_configAdvanced.itemExists("throttle"))
		{
			string throt = m_configAdvanced.getValue("throttle");
			if (throt[0] == 't' || throt[0] == 'T')
			{
				m_throttle = true;
				m_highWater = threshold
				       	+ (((float)threshold * SOUTH_THROTTLE_HIGH_PERCENT) / 100.0);
				m_lowWater = threshold
				       	+ (((float)threshold * SOUTH_THROTTLE_LOW_PERCENT) / 100.0);
				logger->info("Throttling is enabled, high water mark is set to %ld", m_highWater);
			}
			else
			{
				m_throttle = false;
			}
		}
		if (m_configAdvanced.itemExists("assetTrackerInterval"))
		{
			string interval = m_configAdvanced.getValue("assetTrackerInterval");
			unsigned long i = strtoul(interval.c_str(), NULL, 10);
			if (m_assetTracker)
				m_assetTracker->tune(i);
		}
	}

	// Update the  Security category
	if (categoryName.compare(m_name+"Security") == 0)
	{
		this->updateSecurityCategory(category);
	}
}

/**
 * Separate thread to run plugin_reconf, to avoid blocking 
 * service's management interface due to long plugin_poll calls
 */
static void reconfThreadMain(void *arg)
{
	SouthService *ss = (SouthService *)arg;
	Logger::getLogger()->info("reconfThreadMain(): Spawned new thread for plugin reconf");
	ss->handlePendingReconf();
	Logger::getLogger()->info("reconfThreadMain(): plugin reconf thread exiting");
}

/**
 * Handle configuration change notification; called by reconf thread
 * Waits for some reconf operation(s) to get queued up, then works thru' them
 */
void SouthService::handlePendingReconf()
{
	while (isRunning())
	{
		Logger::getLogger()->debug("SouthService::handlePendingReconf: Going into cv wait");
		mutex mtx;
		unique_lock<mutex> lck(mtx);
		m_cvNewReconf.wait(lck);
		Logger::getLogger()->debug("SouthService::handlePendingReconf: cv wait has completed; some reconf request(s) has/have been queued up");

		while (isRunning())
		{
			unsigned int numPendingReconfs = 0;
			{
				lock_guard<mutex> guard(m_pendingNewConfigMutex);
				numPendingReconfs = m_pendingNewConfig.size();
				if (numPendingReconfs)
					Logger::getLogger()->debug("SouthService::handlePendingReconf(): will process %d entries in m_pendingNewConfig", numPendingReconfs);
				else
				{
					Logger::getLogger()->debug("SouthService::handlePendingReconf DONE");
					break;
				}
			}

			for (unsigned int i=0; i<numPendingReconfs; i++)
			{
				logger->debug("SouthService::handlePendingReconf(): Handling Configuration change #%d", i);
				std::pair<std::string,std::string> *reconfValue = NULL;
				{
					lock_guard<mutex> guard(m_pendingNewConfigMutex);
					reconfValue = &m_pendingNewConfig[i];
				}
				std::string categoryName = reconfValue->first;
				std::string category = reconfValue->second;
				processConfigChange(categoryName, category);

				logger->debug("SouthService::handlePendingReconf(): Handling of configuration change #%d done", i);
			}
			
			{
				lock_guard<mutex> guard(m_pendingNewConfigMutex);
				for (unsigned int i=0; i<numPendingReconfs; i++)
					m_pendingNewConfig.pop_front();
				logger->debug("SouthService::handlePendingReconf DONE: first %d entry(ies) removed, m_pendingNewConfig new size=%d", numPendingReconfs, m_pendingNewConfig.size());
			}
		}
	}
}

/**
 * Configuration change notification using a separate thread
 *
 * @param categoryName	Category name
 * @param category	Category value
 */
void SouthService::configChange(const string& categoryName, const string& category)
{
	{
		lock_guard<mutex> guard(m_pendingNewConfigMutex);
		m_pendingNewConfig.emplace_back(std::make_pair(categoryName, category));
		Logger::getLogger()->debug("SouthService::reconfigure(): After adding new entry, m_pendingNewConfig.size()=%d", m_pendingNewConfig.size());

		m_cvNewReconf.notify_all();
	}
}

/**
 * Add the generic south service configuration options to the advanced
 * category
 *
 * @param defaultConfiguration	The default configuration from the plugin
 */
void SouthService::addConfigDefaults(DefaultConfigCategory& defaultConfig)
{
	bool isAsync = southPlugin->isAsync();
	for (int i = 0; defaults[i].name; i++)
	{
		if (strcmp(defaults[i].name, "readingsPerSec") == 0 && isAsync)
		{
			continue;
		}
		defaultConfig.addItem(defaults[i].name, defaults[i].description,
			defaults[i].type, defaults[i].value, defaults[i].value);
		defaultConfig.setItemDisplayName(defaults[i].name, defaults[i].displayName);
		if (!strcmp(defaults[i].name, "readingsPerSec"))
		{
			defaultConfig.setItemAttribute(defaults[i].name, ConfigCategory::MINIMUM_ATTR, "1");

		}
	}

	if (!isAsync)
	{
		/* Add the reading rate units */
		vector<string>	rateUnits = { "second", "minute", "hour" };
		defaultConfig.addItem("units", "Reading Rate Per",
				"second", "second", rateUnits);
		defaultConfig.setItemDisplayName("units", "Reading Rate Per");

		/* Now add the fixed time polling option */
		vector<string> pollOptions = { "Interval", "Fixed Times", "On Demand" };
		defaultConfig.addItem("pollType", "Either poll at fixed intervals, at fixed times or when trigger by a poll control operation.",
				"Interval", "Interval", pollOptions);
		defaultConfig.setItemDisplayName("pollType", "Poll Type");

		/* Add the validity for interval polling items */
		defaultConfig.setItemAttribute("readingsPerSec",
				ConfigCategory::VALIDITY_ATTR, "pollType == \"Interval\"");
		defaultConfig.setItemAttribute("units",
				ConfigCategory::VALIDITY_ATTR, "pollType == \"Interval\"");
		defaultConfig.setItemAttribute("throttle",
				ConfigCategory::VALIDITY_ATTR, "pollType == \"Interval\"");

		/* Add the three time specifiers */
		defaultConfig.addItem("pollHours",
				"List of hours on which to poll or leave empty for all hours",
				"string", "", "");
		defaultConfig.setItemDisplayName("pollHours", "Hours");
		defaultConfig.setItemAttribute("pollHours",
				ConfigCategory::VALIDITY_ATTR, "pollType == \"Fixed Times\"");
		defaultConfig.addItem("pollMinutes",
				"List of minutes on which to poll or leave empty for all minutes",
				"string", "", "");
		defaultConfig.setItemDisplayName("pollMinutes", "Minutes");
		defaultConfig.setItemAttribute("pollMinutes",
				ConfigCategory::VALIDITY_ATTR, "pollType == \"Fixed Times\"");
		defaultConfig.addItem("pollSeconds",
				"Seconds on which to poll expressed as a comma seperated list",
				"string", "0,15,30,45", "0,15,30,40");
		defaultConfig.setItemDisplayName("pollSeconds", "Seconds");
		defaultConfig.setItemAttribute("pollSeconds",
				ConfigCategory::VALIDITY_ATTR, "pollType == \"Fixed Times\"");
	}

	if (southPlugin->hasControl())
	{
		defaultConfig.addItem("control", "Allow write and control operations on the device",
			       "boolean", "true", "true");
		defaultConfig.setItemDisplayName("control", "Allow Control");
	}

	/* Add the set of logging levels to the service */
	vector<string>	logLevels = { "error", "warning", "info", "debug" };
	defaultConfig.addItem("logLevel", "Minimum logging level reported",
			"warning", "warning", logLevels);
	defaultConfig.setItemDisplayName("logLevel", "Minimum Log Level");

	/* Add the set of logging levels to the service */
	vector<string>	statistics = { "per asset", "per service", "per asset & service" };
	defaultConfig.addItem("statistics", "Collect statistics either for every asset ingested, for the service in total or both",
			"per asset & service", "per asset & service", statistics);
	defaultConfig.setItemDisplayName("statistics", "Statistics Collection");
	defaultConfig.addItem("perfmon", "Track and store performance counters",
			       "boolean", "false", "false");
	defaultConfig.setItemDisplayName("perfmon", "Performance Counters");
}

/**
 * Create a timer FD on which a read would return data every time the given 
 * interval elapses
 *
 * @param usecs	 Time in micro-secs after which data would be available on the timer FD
 */
int SouthService::createTimerFd(struct timeval rate)
{
	int fd = -1;
	struct itimerspec new_value;
	struct timespec now;

	if (clock_gettime(CLOCK_REALTIME, &now) == -1)
	   Logger::getLogger()->error("clock_gettime");

	new_value.it_value.tv_sec = now.tv_sec + rate.tv_sec;
	new_value.it_value.tv_nsec = now.tv_nsec + rate.tv_usec*1000;
	if (new_value.it_value.tv_nsec >= 1000000000)
	{
		new_value.it_value.tv_sec += new_value.it_value.tv_nsec/1000000000;
		new_value.it_value.tv_nsec %= 1000000000;
	}
	
	new_value.it_interval.tv_sec = rate.tv_sec;
	new_value.it_interval.tv_nsec = rate.tv_usec*1000;
	if (new_value.it_interval.tv_nsec >= 1000000000)
	{
		new_value.it_interval.tv_sec += new_value.it_interval.tv_nsec/1000000000;
		new_value.it_interval.tv_nsec %= 1000000000;
	}
	
	errno=0;
	fd = timerfd_create(CLOCK_REALTIME, 0);
	if (fd == -1)
	{
		Logger::getLogger()->error("timerfd_create failed, errno=%d (%s)", errno, strerror(errno));
		return fd;
	}

	if (timerfd_settime(fd, TFD_TIMER_ABSTIME, &new_value, NULL) == -1)
	{
	    Logger::getLogger()->error("timerfd_settime failed, errno=%d (%s)", errno, strerror(errno));
	    close (fd);
		return -1;
	}

	return fd;
}

/**
 * If enabled, control the throttling of the poll rate in order to keep
 * the buffer usage of the service within check.
 *
 * Although this is written as if rate is being control, which it
 * logically is, the actual values are poll intervals. Hence reducing
 * the poll rate increases the value of m_currentRate.
 */
void SouthService::throttlePoll()
{
struct timeval now, res;

	if (!m_throttle)
	{
		return;
	}
	double desired = m_desiredRate.tv_sec + ((double)m_desiredRate.tv_usec / 1000000);
	desired *= m_repeatCnt;
	gettimeofday(&now, NULL);
	timersub(&now, &m_lastThrottle, &res);
	if (m_ingest->queueLength() > m_highWater && res.tv_sec > SOUTH_THROTTLE_DOWN_INTERVAL)
	{
		double rate = m_currentRate.tv_sec + ((double)m_currentRate.tv_usec / 1000000);
		rate *= (1.0 + ((double)SOUTH_THROTTLE_PERCENT / 100.0));
		if (rate > MAX_SLEEP * 1000000)
		{
			double x = rate / (MAX_SLEEP * 1000000);
			m_repeatCnt = ceil(x);
			rate /= m_repeatCnt;
		}
		else
		{
			m_repeatCnt = 1;
		}
		m_currentRate.tv_sec = (long)rate;
		m_currentRate.tv_usec = (rate - m_currentRate.tv_sec) * 1000000;
		close(m_timerfd);
		m_timerfd = createTimerFd(m_currentRate); // interval to be passed is in usecs
		m_lastThrottle = now;
		m_throttled = true;
		logger->warn("%s Throttled down poll, rate is now %.1f%% of desired rate", m_name.c_str(), (desired * 100) / rate);
		m_perfMonitor->collect("throttled rate", (long)(rate * 1000));
	}
	else if (m_throttled && m_ingest->queueLength() < m_lowWater && res.tv_sec > SOUTH_THROTTLE_UP_INTERVAL)
	{
		// We are currently throttled back but the queue is below the low water mark
		timersub(&m_desiredRate, &m_currentRate, &res);
		if (res.tv_sec != 0 || res.tv_usec != 0)
		{
			double rate = m_currentRate.tv_sec + ((double)m_currentRate.tv_usec / 1000000);
			rate *= (1.0 - ((double)SOUTH_THROTTLE_PERCENT / 100.0));
			if (rate > MAX_SLEEP * 1000000)
			{
				double x = rate / (MAX_SLEEP * 1000000);
				m_repeatCnt = ceil(x);
				rate /= m_repeatCnt;
			}
			else
			{
				m_repeatCnt = 1;
			}
			m_currentRate.tv_sec = (long)rate;
			m_currentRate.tv_usec = (rate - m_currentRate.tv_sec) * 1000000;
			if (m_currentRate.tv_sec <= m_desiredRate.tv_sec
					&& m_currentRate.tv_usec < m_desiredRate.tv_usec)
			{
				m_currentRate = m_desiredRate;
				m_throttled = false;
				logger->warn("%s Poll rate returned to configured value", m_name.c_str());
			}
			else
			{
				logger->warn("%s Throttled up poll, rate is now %.1f%% of desired rate", m_name.c_str(), (desired * 100) / rate);
			}
			m_perfMonitor->collect("throttled rate", (long)(rate * 1000));
			close(m_timerfd);
			m_timerfd = createTimerFd(m_currentRate); // interval to be passed is in usecs
			m_lastThrottle = now;
		}
	}
}

/**
 * Perform a setPoint operation on the south plugin
 *
 * @param name	Name of the point to set
 * @param value	The value to set
 * @return	Success or failure of the SetPoint operation
 */
bool SouthService::setPoint(const string& name, const string& value)
{
	if (southPlugin->hasControl())
	{
		return southPlugin->write(name, value);
	}
	else
	{
		logger->warn("SetPoint operation %s = %s attempted on plugin that does not support control", name.c_str(), value.c_str());
		return false;
	}
}

/**
 * Perform an operation on the south plugin
 *
 * @param name	Name of the operation
 * @param params The parameters for the operaiton, if any
 * @return	Success or failure of the operation
 */
bool SouthService::operation(const string& operation, vector<PLUGIN_PARAMETER *>& params)
{
	if (operation.compare("poll") == 0)
	{
		if (m_pollType == POLL_ON_DEMAND)
		{
			m_doPoll = true;
			m_pollCV.notify_all();
			return true;
		}
		else
		{
			logger->warn("Received a poll request for a service that is not enabled for on demand polling");
			return false;
		}
	}
	else if (southPlugin->hasControl())
	{
		return southPlugin->operation(operation, params);
	}
	else
	{
		logger->warn("Operation %s attempted on plugin that does not support control", operation.c_str());
		return false;
	}
}

/**
 * Process a list of numbers into a vector of integers.
 * The list of numbers is obtained from a configuration
 * item.
 *
 * @param category	The configuration category
 * @param item		Name of the configuration item
 * @param list		The vector to populate
 */
void SouthService::processNumberList(const ConfigCategory& category,
				const string& item, vector<unsigned long>& list)
{
	list.clear();
	if (!category.itemExists(item))
	{
		Logger::getLogger()->warn("Item %s does not exist", item.c_str());
		return;
	}
	string value = category.getValue(item);
	if (value.length() == 0)
	{
		Logger::getLogger()->info("Item %s is empty", item.c_str());
		return;
	}

	const char *ptr = value.c_str();
	char *eptr;
	while (*ptr)
	{
		list.push_back(strtoul(ptr, &eptr, 10));
		ptr = eptr;
		if (*ptr == ',')
			ptr++;
	}
}

/**
 * Calcuate the rate at which the timer should trigger and the repeat
 * requirement needed to match the requested poll rate
 */
void SouthService::calculateTimerRate()
{
	string pollType = m_configAdvanced.getValue("pollType");
	if (pollType.compare("Fixed Times") == 0)
	{
		if (m_pollType == POLL_ON_DEMAND)
		{
			lock_guard<mutex> lk(m_pollMutex);
			m_pollType = POLL_FIXED;
			m_pollCV.notify_all();
		}
		m_pollType = POLL_FIXED;
		processNumberList(m_configAdvanced, "pollHours", m_hours);
		processNumberList(m_configAdvanced, "pollMinutes", m_minutes);
		processNumberList(m_configAdvanced, "pollSeconds", m_seconds);

		if (m_minutes.size() == 0 && m_hours.size() != 0)
			m_minutes.push_back(0);
		if (m_seconds.size() == 0 && m_minutes.size() != 0)
			m_seconds.push_back(0);

		m_desiredRate.tv_sec  = 1;
		m_desiredRate.tv_usec = 0;
	}
	else if (pollType.compare("On Demand") == 0)
	{
		m_pollType = POLL_ON_DEMAND;
	}
	else
	{
		if (m_pollType == POLL_ON_DEMAND)
		{
			lock_guard<mutex> lk(m_pollMutex);
			m_pollType = POLL_INTERVAL;
			m_pollCV.notify_all();
		}
		m_pollType = POLL_INTERVAL;
		string units = m_configAdvanced.getValue("units");
		unsigned long dividend = 1000000;
		if (units.compare("second") == 0)
			dividend = 1000000;
		else if (units.compare("minute") == 0)
			dividend = 60000000;
		else if (units.compare("hour") == 0)
			dividend = 3600000000;
		m_rateUnits = units;
		unsigned long usecs = dividend / m_readingsPerSec;

		if (usecs > MAX_SLEEP * 1000000)
		{
			double x = usecs / (MAX_SLEEP * 1000000);
			m_repeatCnt = ceil(x);
			usecs /= m_repeatCnt;
		}
		else
		{
			m_repeatCnt = 1;
		}
		m_desiredRate.tv_sec  = (int)(usecs / 1000000);
		m_desiredRate.tv_usec = (int)(usecs % 1000000);
	}
}

/**
 * Find the next fixed time poll time and wait for that time before returning.
 * This method will also return if m_shutdown is set.
 *
 * @return bool	True if the return is doe to a poll being required.
 */
bool SouthService::syncToNextPoll()
{
	time_t tim = time(0);
	struct tm tm;
	localtime_r(&tim, &tm);
	unsigned long waitFor = 1;

	if (m_hours.size() == 0 && m_minutes.size() == 0 && m_seconds.size() == 0)
	{
		Logger::getLogger()->error("Poll time misconfigured.");
	}
	else if (m_hours.size() == 0 && m_minutes.size() == 0)
	{
		// Only looking at seconds
		unsigned int i;
		for (i = 0; i < m_seconds.size() && m_seconds[i] <= (unsigned)tm.tm_sec; i++)
		{
		}
		if (i == m_seconds.size())
		{
			waitFor = (60 - (unsigned)tm.tm_sec) + m_seconds[0];
		}
		else
		{
			waitFor = m_seconds[i] - (unsigned)tm.tm_sec;
		}
	}
	else if (m_hours.size() == 0)
	{
		unsigned int target_min = (unsigned)tm.tm_min;
		unsigned int min, sec;
		for (min = 0; min < m_minutes.size() && m_minutes[min] < target_min; min++)
		{
		}
		if (min == m_minutes.size()) // Reset to start of minute list
		{
			min = 0;
		}

		if (m_minutes[min] != target_min)	// Not this minute
		{
			sec = 0;	// Always use first setting of seconds
		}
		else
		{
			for (sec = 0; sec < m_seconds.size() && m_seconds[sec] <= (unsigned)tm.tm_sec; sec++)
			{
			}
			if (sec == m_seconds.size())
			{
				// Too late in this minute use next minute setting
				sec = 0;
				min++;
				if (min >= m_minutes[min])
				{
					min = 0;
				}
			}
		}
		waitFor = 0;
		if (m_minutes[min] > (unsigned)tm.tm_min)
		{
			waitFor = 60 * (m_minutes[min] - (unsigned)tm.tm_min);
		}
		else if (m_minutes[min] < (unsigned)tm.tm_min)
		{
			waitFor = 60 * ((60 - (unsigned)tm.tm_min) + m_minutes[min]);
		}
		if (m_seconds[sec] > (unsigned)tm.tm_sec)
		{
			waitFor += ((unsigned)tm.tm_sec - m_seconds[sec]);
		}
		else
		{
			waitFor += ((60 - (unsigned)tm.tm_sec) + m_seconds[sec]);
		}
	}
	else	// Hours, minutes and seconds
	{
		unsigned int hour, min, sec;
		for (hour = 0; hour < m_hours.size() && m_hours[hour] < (unsigned)tm.tm_hour; hour++)
		{
		}
		if (hour == m_hours.size()) // Reset to start of minute list
		{
			min = 0;
			sec = 0;
			hour = 0;
		}
		else if (m_hours[hour] == (unsigned)tm.tm_hour)	// Check for this hour
		{
			for (min = 0; min < m_minutes.size() && m_minutes[min] < (unsigned)tm.tm_min; min++)
			{
			}
			if (min < m_minutes.size()) // may still be a trogger in this hor
			{
				for (sec = 0; sec < m_seconds.size() && m_seconds[sec] <= (unsigned)tm.tm_sec; sec++)
				{
				}
				if (sec == m_seconds.size())
				{
					// Too late in this minute use next minute setting
					sec = 0;
					min++;
					if (min == m_minutes.size())
					{
						min = 0;
						sec = 0;
						hour++;
						if (m_hours.size() == hour)
							hour = 0;
					}
				}
			}
			else
			{
				hour++;
				min = 0;
				sec = 0;
				if (m_hours.size() == hour)
					hour = 0;
			}
		}
		else
		{
			hour++;
			min = 0;
			sec = 0;
			if (m_hours.size() == hour)
				hour = 0;
		}
		waitFor = 0;
		if (m_hours[hour] > (unsigned)tm.tm_hour)
		{
			waitFor += 60 * 60 * (m_hours[hour] - (unsigned)tm.tm_hour);
		}
		else if (m_minutes[min] < (unsigned)tm.tm_min)
		{
			waitFor += 60 * 60 * ((24 - (unsigned)tm.tm_hour) + m_hours[hour]);
		}
		if (m_minutes[min] > (unsigned)tm.tm_min)
		{
			waitFor += 60 * (m_minutes[min] - (unsigned)tm.tm_min);
		}
		else if (m_minutes[min] < (unsigned)tm.tm_min)
		{
			waitFor += 60 * ((60 - (unsigned)tm.tm_min) + m_minutes[min]);
		}
		if (m_seconds[sec] > (unsigned)tm.tm_sec)
		{
			waitFor += ((unsigned)tm.tm_sec - m_seconds[sec]);
		}
		else
		{
			waitFor += ((60 - (unsigned)tm.tm_sec) + m_seconds[sec]);
		}
	}


	uint64_t exp;
	while (waitFor)
	{
		if (read(m_timerfd, &exp, sizeof(uint64_t)) == -1)
			return false;
		waitFor--;
		if (m_shutdown)
			return false;
		if (m_pollType != POLL_FIXED)	// Configuration has change to the poll type
		{
			return false;
		}
	}
	return true;
}

/**
 * Wait until either a shutdown request is received or a poll operation
 *
 * @return bool		True if the return is due to a new poll request
 */
bool SouthService::onDemandPoll()
{
	unique_lock<mutex> lk(m_pollMutex);
	if (! m_shutdown)
	{
		m_doPoll = false;
		m_pollCV.wait(lk);
	}
	return m_doPoll;
}

/**
 * Check to see if there is a reconfiguration option blocking in another
 * thread and yield until that reconfiguration has occured.
 */
void SouthService::checkPendingReconfigure()
{
	while(1)
	{
		unsigned int numPendingReconfs;
		{
			lock_guard<mutex> guard(m_pendingNewConfigMutex);
			numPendingReconfs = m_pendingNewConfig.size();
		}
		// if a reconf is pending, make this poll thread yield CPU, sleep_for is needed to sleep this thread for sufficiently long time
		if (numPendingReconfs)
		{
			Logger::getLogger()->debug("SouthService::start(): %d entries in m_pendingNewConfig, poll thread yielding CPU", numPendingReconfs);
			std::this_thread::sleep_for(std::chrono::milliseconds(200));
		}
		else
			return;
	}
}

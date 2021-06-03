/*
 * Fledge storage service.
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

extern int makeDaemon(void);
extern void handler(int sig);

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
	}

	if (daemonMode && makeDaemon() == -1)
	{
		// Failed to run in daemon mode
		cout << "Failed to run as deamon - proceeding in interactive mode." << endl;
	}

	SouthService *service = new SouthService(myName, token);
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
 * Callback called by south plugin to ingest readings into Fledge
 *
 * @param ingest	The ingest class to use
 * @param reading	The Reading to ingest
 */
void doIngest(Ingest *ingest, Reading reading)
{
	ingest->ingest(reading);
}

void doIngestV2(Ingest *ingest, const vector<Reading *> *vec)
{
	ingest->ingest(vec);
}


/**
 * Constructor for the south service
 */
SouthService::SouthService(const string& myName, const string& token) :
				m_name(myName),
				m_shutdown(false),
				m_readingsPerSec(1),
				m_throttle(false),
				m_throttled(false),
				m_token(token)
{
	logger = new Logger(myName);
	logger->setMinLevel("warning");
}

ManagementClient *SouthService::m_mgtClient = NULL;

ManagementClient * SouthService::getMgmtClient()
{
	return m_mgtClient;
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
					"Southbound",		// Service type
					"http",			// Protocol
					"localhost",		// Listening address
					sport,			// Service port
					managementListener,	// Management port
					m_token);		// Token
		m_mgtClient = new ManagementClient(coreAddress, corePort);

		// Create an empty South category if one doesn't exist
		DefaultConfigCategory southConfig(string("South"), string("{}"));
		southConfig.setDescription("South");
		m_mgtClient->addCategory(southConfig, true);

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

		
		StorageClient storage(storageRecord.getAddress(),
						storageRecord.getPort());
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
				logger->setMinLevel(m_configAdvanced.getValue("logLevel"));
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

		{
		// Instantiate the Ingest class
		Ingest ingest(storage, timeout, threshold, m_name, pluginName, m_mgtClient);
		m_ingest = &ingest;

		try {
			m_readingsPerSec = 1;
			if (m_configAdvanced.itemExists("readingsPerSec"))
				m_readingsPerSec = (unsigned long)strtol(m_configAdvanced.getValue("readingsPerSec").c_str(), NULL, 10);
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

		// Get and ingest data
		if (! southPlugin->isAsync())
		{
			string units = m_configAdvanced.getValue("units");
			unsigned long dividend = 1000000;
			if (units.compare("second") == 0)
				dividend = 1000000;
			else if (units.compare("minute") == 0)
				dividend = 60000000;
			else if (units.compare("hour") == 0)
				dividend = 3600000000;
			unsigned long usecs = dividend / m_readingsPerSec;
			m_desiredRate.tv_sec  = (int)(usecs / 1000000);
			m_desiredRate.tv_usec = (int)(usecs % 1000000);
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

			while (!m_shutdown)
			{
				uint64_t exp;
				ssize_t s;
				
				s = read(m_timerfd, &exp, sizeof(uint64_t));
				if ((unsigned int)s != sizeof(uint64_t))
					logger->error("timerfd read()");
				if (exp > 100 && exp > m_readingsPerSec/2)
					logger->error("%d expiry notifications accumulated", exp);
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
						vector<Reading *> *vec = southPlugin->pollV2();
						if (!vec) continue;
						ingest.ingest(vec);
						pollCount += (int) vec->size();
						delete vec; 	// each reading object inside vector has been allocated on heap and moved to Ingest class's internal queue
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
					southPlugin->start();
					started = true;
				} catch (...) {
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

		// Shutdown the API
		delete api;

		// do plugin shutdown before destroying Ingest object on stack
		if (southPlugin)
			southPlugin->shutdown();
		}
		
		// Clean shutdown, unregister the storage service
		m_mgtClient->unregisterService();
	}
	management.stop();
	logger->info("South service shutdown completed");
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
	m_shutdown = true;
	logger->info("South service shutdown in progress.");
}

/**
 * Configuration change notification
 */
void SouthService::configChange(const string& categoryName, const string& category)
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
		if (! southPlugin->isAsync())
		{
			try {
				unsigned long newval = (unsigned long)strtol(m_configAdvanced.getValue("readingsPerSec").c_str(), NULL, 10);
				string units = m_configAdvanced.getValue("units");
				unsigned long dividend = 1000000;
				if (units.compare("second") == 0)
					dividend = 1000000;
				else if (units.compare("minute") == 0)
					dividend = 60000000;
				else if (units.compare("hour") == 0)
					dividend = 3600000000;
				if (newval != m_readingsPerSec)
				{
					m_readingsPerSec = newval;
					close(m_timerfd);
					unsigned long usecs = dividend / m_readingsPerSec;
					m_desiredRate.tv_sec  = (int)(usecs / 1000000);
					m_desiredRate.tv_usec = (int)(usecs % 1000000);
					m_currentRate = m_desiredRate;
					m_timerfd = createTimerFd(m_desiredRate); // interval to be passed is in usecs
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
			logger->setMinLevel(m_configAdvanced.getValue("logLevel"));
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
	}

	if (!isAsync)
	{
		/* Add the reading rate units */
		vector<string>	rateUnits = { "second", "minute", "hour" };
		defaultConfig.addItem("units", "Reading Rate Per",
				"second", "second", rateUnits);
		defaultConfig.setItemDisplayName("units", "Reading Rate Per");
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
	gettimeofday(&now, NULL);
	timersub(&now, &m_lastThrottle, &res);
	if (m_ingest->queueLength() > m_highWater && res.tv_sec > SOUTH_THROTTLE_DOWN_INTERVAL)
	{
		double rate = m_currentRate.tv_sec + ((double)m_currentRate.tv_usec / 1000000);
		rate *= (1.0 + ((double)SOUTH_THROTTLE_PERCENT / 100.0));
		m_currentRate.tv_sec = (long)rate;
		m_currentRate.tv_usec = (rate - m_currentRate.tv_sec) * 1000000;
		close(m_timerfd);
		m_timerfd = createTimerFd(m_currentRate); // interval to be passed is in usecs
		m_lastThrottle = now;
		m_throttled = true;
		logger->warn("%s Throttled down poll, rate is now %.1f%% of desired rate", m_name.c_str(), (desired * 100) / rate);
	}
	else if (m_throttled && m_ingest->queueLength() < m_lowWater && res.tv_sec > SOUTH_THROTTLE_UP_INTERVAL)
	{
		// We are current throttle back but the queue is below the low water mark
		timersub(&m_desiredRate, &m_currentRate, &res);
		if (res.tv_sec != 0 || res.tv_usec != 0)
		{
			double rate = m_currentRate.tv_sec + ((double)m_currentRate.tv_usec / 1000000);
			rate *= (1.0 - ((double)SOUTH_THROTTLE_PERCENT / 100.0));
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
	if (southPlugin->hasControl())
	{
		return southPlugin->operation(operation, params);
	}
	else
	{
		logger->warn("Operation %s attempted on plugin that does not support control", operation.c_str());
		return false;
	}
}

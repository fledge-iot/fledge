/*
 * FogLAMP storage service.
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
 * Callback called by south plugin to ingest readings into FogLAMP
 *
 * @param ingest	The ingest class to use
 * @param reading	The Reading to ingest
 */
void doIngest(Ingest *ingest, Reading reading)
{
	ingest->ingest(reading);
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
		ServiceRecord storageRecord("FogLAMP Storage");
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
		std::string pluginName;
		try {
			if (m_config.itemExists("bufferThreshold"))
				threshold = (unsigned int)atoi(m_config.getValue("bufferThreshold").c_str());
			if (m_config.itemExists("maxSendLatency"))
				timeout = (unsigned long)atoi(m_config.getValue("maxSendLatency").c_str());
			if (m_config.itemExists("plugin"))
				pluginName = m_config.getValue("plugin");
		} catch (ConfigItemNotFound e) {
			logger->info("Defaulting to inline defaults for south configuration");
		}

		// Instantiate the Ingest class
		Ingest ingest(storage, timeout, threshold, m_name, pluginName, m_mgtClient);

		try {
			m_pollInterval = 500;
			if (m_config.itemExists("pollInterval"))
				m_pollInterval = (unsigned long)atoi(m_config.getValue("pollInterval").c_str());
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
			int fd = createTimerFd(m_pollInterval * 1000); // interval to be passed is in usecs
			if (fd >= 0)
				logger->info("Created timer FD with interval of %u usecs", m_pollInterval * 1000);
			else
			{
				logger->fatal("Could not create timer FD");
				return;
			}
			
			int pollCount = 0;
			struct timespec start, end;
			if (clock_gettime(CLOCK_MONOTONIC, &start) == -1)
			   Logger::getLogger()->error("polling loop start: clock_gettime");

			while (!m_shutdown)
			{
				uint64_t exp;
				ssize_t s;
				
				s = read(fd, &exp, sizeof(uint64_t));
				if (s != sizeof(uint64_t))
					logger->error("timerfd read()");
				if (exp > 100)
					logger->error("%d expiry notifications accumulated", exp);
				for (uint64_t i=0; i<exp; i++)
				{
					Reading reading = southPlugin->poll();
					ingest.ingest(reading);
					++pollCount;
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
			close(fd);
		}
		else
		{
			southPlugin->registerIngest((INGEST_CB)doIngest, &ingest);
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
 * Create a timer FD on which a read would return data every time the given 
 * interval elapses
 *
 * @param usecs	 Time in micro-secs after which data would be available on the timer FD
 */
int SouthService::createTimerFd(unsigned int usecs)
{
	int fd = -1;
	struct itimerspec new_value;
	struct timespec now;
	
	if (clock_gettime(CLOCK_REALTIME, &now) == -1)
	   Logger::getLogger()->error("clock_gettime");

	new_value.it_value.tv_sec = now.tv_sec;
	new_value.it_value.tv_nsec = now.tv_nsec + usecs*1000;
	if (new_value.it_value.tv_nsec >= 1000000000)
	{
		new_value.it_value.tv_sec += new_value.it_value.tv_nsec/1000000000;
		new_value.it_value.tv_nsec %= 1000000000;
	}
	
	new_value.it_interval.tv_sec = 0;
	new_value.it_interval.tv_nsec = usecs*1000;
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


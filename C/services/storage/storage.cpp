/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <storage_service.h>
#include <configuration.h>
#include <management_api.h>
#include <management_client.h>
#include <service_record.h>
#include <plugin_manager.h>
#include <plugin_api.h>
#include <plugin.h>
#include <logger.h>
#include <iostream>
#include <string>
#include <signal.h>
#include <execinfo.h>
#include <dlfcn.h>
#include <cxxabi.h>
#include <syslog.h>
#include <config_handler.h>
#include <plugin_configuration.h>

#define NO_EXIT_STACKTRACE		0	// Set to 1 to make storage loop after stacktrace
						// This is useful to be able to attach a debbugger

extern int makeDaemon(void);

using namespace std;

/**
 * Signal handler to log stack trqaces on fatal signals
 */
static void handler(int sig)
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
#if NO_EXIT_STACKTRACE
	while (1)
	{
		sleep(100);
	}
#endif
	exit(1);
}


/**
 * Storage service main entry point
 */
int main(int argc, char *argv[])
{
unsigned short corePort = 8082;
string	       coreAddress = "localhost";
bool	       daemonMode = true;
string	       myName = SERVICE_NAME;
bool           returnPlugin = false;
bool           returnReadingsPlugin = false;
string	       logLevel = "warning";

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
		else if (!strncmp(argv[i], "--plugin", 8))
		{
			returnPlugin = true;
		}
		else if (!strncmp(argv[i], "--readingsplugin", 8))
		{
			returnReadingsPlugin = true;
		}
		else if (!strncmp(argv[i], "--logLevel=", 11))
		{
			logLevel = &argv[i][11];
		}
	}

#ifdef PROFILING
	char profilePath[200]{0};
	if (getenv("FLEDGE_DATA")) 
	{
		snprintf(profilePath, sizeof(profilePath), "%s/%s_Profile", getenv("FLEDGE_DATA"), myName.c_str());
	} else if (getenv("FLEDGE_ROOT"))
	{
		snprintf(profilePath, sizeof(profilePath), "%s/data/%s_Profile", getenv("FLEDGE_ROOT"), myName.c_str());
	} else 
	{
		snprintf(profilePath, sizeof(profilePath), "/usr/local/fledge/data/%s_Profile", myName.c_str());
	}
	mkdir(profilePath, 0777);
	chdir(profilePath);
#endif

	if (returnPlugin == false && returnReadingsPlugin == false && daemonMode && makeDaemon() == -1)
	{
		// Failed to run in daemon mode
		cout << "Failed to run as deamon - proceeding in interactive mode." << endl;
	}

	if (returnPlugin && returnReadingsPlugin)
	{
		cout << "You can not specify --plugin and --readingsplugin together";
		exit(1);
	}

	StorageService service(myName);
	service.setLogLevel(logLevel);
	Logger::getLogger()->setMinLevel(logLevel);
	if (returnPlugin)
	{
		cout << service.getPluginName() << " " << service.getPluginManagedStatus() << endl;
	}
	else if (returnReadingsPlugin)
	{
		cout << service.getReadingPluginName() << " " << service.getPluginManagedStatus() << endl;
	}
	else
	{
		service.start(coreAddress, corePort);
	}
	return 0;
}

/**
 * Detach the process from the terminal and run in the background.
 */
int makeDaemon()
{
pid_t pid;

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

	// If we got here we are a child process

	// create new session and process group 
	if (setsid() == -1)  
	{
		return -1;  
	}
	setlogmask(logmask);

	// Close stdin, stdout and stderr
	close(0);
	close(1);
	close(2);
	// redirect fd's 0,1,2 to /dev/null
	(void)open("/dev/null", O_RDWR);  	// stdin
	if (dup(0) == -1) {}  			// stdout	Workaround GCC bug 66425 produces warning
	if (dup(0) == -1) {}  			// stderr	Workaround GCC bug 66425 produces warning
 	return 0;
}

/**
 * Constructor for the storage service
 */
StorageService::StorageService(const string& myName) : m_name(myName),
						readingPlugin(NULL), m_shutdown(false),
						m_requestRestart(false)
{
unsigned short servicePort;

	config = new StorageConfiguration();
	logger = new Logger(myName);

	signal(SIGSEGV, handler);
	signal(SIGILL, handler);
	signal(SIGBUS, handler);
	signal(SIGFPE, handler);
	signal(SIGABRT, handler);

	if (config->getValue("port") == NULL)
	{
		servicePort = 0;	// default to a dynamic port
	}
	else
	{
		servicePort = (unsigned short)atoi(config->getValue("port"));
	}
	unsigned int threads = 1;
	if (config->hasValue("threads"))
	{
		threads = (unsigned int)atoi(config->getValue("threads"));
	}
	unsigned int workerPoolSize = 5;
	if (config->hasValue("workerPool"))
	{
		workerPoolSize = (unsigned int)atoi(config->getValue("workerPool"));
	}
	if (config->hasValue("logLevel"))
	{
		m_logLevel = config->getValue("logLevel");
	}
	else
	{
		m_logLevel = "warning";
	}
	logger->setMinLevel(m_logLevel);

	if (config->hasValue("timeout"))
	{
		m_timeout = strtol(config->getValue("timeout"), NULL, 10);
	}
	else
	{
		m_timeout = 5;
	}

	api = new StorageApi(servicePort, threads, workerPoolSize);
	api->setTimeout(m_timeout);
}

/**
 * Storage Service destructor
 */
StorageService::~StorageService()
{
	delete api;
	delete config;
	delete logger;
}

/**
 * Start the storage service
 */
void StorageService::start(string& coreAddress, unsigned short corePort)
{
	if (!loadPlugin())
	{
		logger->fatal("Failed to load storage plugin.");
		return;
	}
	unsigned short managementPort = (unsigned short)0;
	if (config->getValue("managementPort"))
	{
		managementPort = (unsigned short)atoi(config->getValue("managementPort"));
	}
	ManagementApi management(SERVICE_NAME, managementPort);	// Start managemenrt API
	api->initResources();
	logger->info("Starting service...");
	api->start();
	management.registerService(this);

	management.start();

	// Allow time for the listeners to start before we register
	sleep(1);
	if (! m_shutdown)
	{
		// Now register our service
		// TODO proper hostname lookup
		unsigned short listenerPort = api->getListenerPort();
		unsigned short managementListener = management.getListenerPort();
		ServiceRecord record(m_name, "Storage", "http", "localhost", listenerPort, managementListener);
		ManagementClient *client = new ManagementClient(coreAddress, corePort);
		client->registerService(record);

		// FOGL-7074 upgrade step
		try {
			ConfigCategory cat = client->getCategory("Storage");
			string rp = cat.getValue("readingPlugin");
			if (rp.empty())
			{
				client->setCategoryItemValue("Storage", "readingPlugin",
						"Use main plugin");
			}
		} catch (...) {
			// ignore
		}

		// Add the default configuration under the Advanced category
		unsigned int retryCount = 0;
		DefaultConfigCategory *conf = config->getDefaultCategory();
		conf->setDescription(CATEGORY_DESCRIPTION);
		while (client->addCategory(*conf, false) == false && ++retryCount < 10)
		{
			sleep(2 * retryCount);
		}

		delete conf;

		vector<string> children1;
		children1.push_back(STORAGE_CATEGORY);
		ConfigCategories categories = client->getCategories();
		try {
			bool found = false;
			for (unsigned int idx = 0; idx < categories.length(); idx++)
			{
				if (categories[idx]->getName().compare(ADVANCED) == 0)
				{
					client->addChildCategories(ADVANCED, children1);
					found = true;
				}
			}
			if (!found)
			{
				DefaultConfigCategory advanced(ADVANCED, "{}");
				advanced.setDescription(ADVANCED);
				if (client->addCategory(advanced, true))
				{
					client->addChildCategories(ADVANCED, children1);
				}
			}
		} catch (...) {
		}

		// Register for configuration changes to our category
		ConfigHandler *configHandler = ConfigHandler::getInstance(client);
		configHandler->registerCategory(this, STORAGE_CATEGORY);

		StoragePluginConfiguration *storagePluginConfig = storagePlugin->getConfig();
		if (storagePluginConfig != NULL)
		{
			DefaultConfigCategory *conf = storagePluginConfig->getDefaultCategory();
			conf->setDescription("Storage Plugin");
			while (client->addCategory(*conf, true) == false && ++retryCount < 10)
			{
				sleep(2 * retryCount);
			}
			vector<string> children1;
			children1.push_back(conf->getName());
			client->addChildCategories(STORAGE_CATEGORY, children1);

			// Register for configuration changes to our storage plugin category
			ConfigHandler *configHandler = ConfigHandler::getInstance(client);
			configHandler->registerCategory(this, conf->getName());

			delete conf;
		}
		if (readingPlugin)
		{
			StoragePluginConfiguration *storagePluginConfig = readingPlugin->getConfig();
			if (storagePluginConfig != NULL)
			{
				StoragePluginConfiguration *storagePluginConfig = readingPlugin->getConfig();
				if (storagePluginConfig != NULL)
				{
					DefaultConfigCategory *conf = storagePluginConfig->getDefaultCategory();
					conf->setDescription("Reading Plugin");
					while (client->addCategory(*conf, true) == false && ++retryCount < 10)
					{
						sleep(2 * retryCount);
					}
					vector<string> children1;
					children1.push_back(conf->getName());
					client->addChildCategories(STORAGE_CATEGORY, children1);

					// Regsiter for configuration changes to our reading category category
					ConfigHandler *configHandler = ConfigHandler::getInstance(client);
					configHandler->registerCategory(this, conf->getName());
				}
			}
		}

		// Now we are running force the plugin names back to the configuration manager to
		// make sure they match what we are running. This can be out of sync if the storage
		// configuration cache has been manually reset or altered while Fledge was down
		client->setCategoryItemValue(STORAGE_CATEGORY, "plugin", config->getValue("plugin"));
		client->setCategoryItemValue(STORAGE_CATEGORY, "readingPlugin", config->getValue("readingPlugin"));

		// Check whether to enable storage performance monitor
		if (config->hasValue("perfmon"))
		{
			string perf = config->getValue("perfmon");
			if (perf.compare("true") == 0)
			{
				api->getPerformanceMonitor()->setCollecting(true);
			}
			else
			{
				api->getPerformanceMonitor()->setCollecting(false);
			}
		}

		// Wait for all the API threads to complete
		api->wait();

		if (readingPlugin)
			readingPlugin->pluginShutdown();
		readingPlugin = NULL;

		if (storagePlugin)
			storagePlugin->pluginShutdown();
		storagePlugin = NULL;

		// Clean shutdown, unregister the storage service
		if (m_requestRestart)
			client->restartService();
		else
			client->unregisterService();
	}
	else
	{
		api->wait();
	}
	management.stop();
	logger->info("Storage service shut down.");
}

/**
 * Stop the storage service/
 */
void StorageService::stop()
{
	logger->info("Stopping service...\n");
}

/**
 * Load the configured storage plugin or plugins
 *
 * @return bool	True if the plugins have been loaded and support the correct operations
 */
bool StorageService::loadPlugin()
{
	PluginManager *manager = PluginManager::getInstance();
	manager->setPluginType(PLUGIN_TYPE_ID_STORAGE);

	const char *plugin = config->getValue("plugin");
	if (plugin == NULL)
	{
		logger->error("Unable to fetch plugin name from configuration.\n");
		return false;
	}
	logger->info("Load storage plugin %s.", plugin);
	PLUGIN_HANDLE handle;
	string	pname = plugin;
	if ((handle = manager->loadPlugin(pname, PLUGIN_TYPE_STORAGE)) != NULL)
	{
		storagePlugin = new StoragePlugin(pname, handle);
		if ((storagePlugin->getInfo()->options & SP_COMMON) == 0)
		{
			logger->error("Defined storage plugin %s does not support common table operations.\n",
					plugin);
			return false;
		}
		if (config->hasValue("raedingPlugin") == false && (storagePlugin->getInfo()->options & SP_READINGS) == 0)
		{
			logger->error("Defined storage plugin %s does not support readings operations.\n",
					plugin);
			return false;
		}
		api->setPlugin(storagePlugin);
		logger->info("Loaded storage plugin %s.", plugin);
	}
	else
	{
		return false;
	}
	if (! config->hasValue("readingPlugin"))
	{
		// Single plugin does everything
		return true;
	}
	const char *readingPluginName = config->getValue("readingPlugin");
	if (! *readingPluginName)
	{
		// Single plugin does everything
		return true;
	}
       	if (strcmp(readingPluginName, plugin) == 0 
			|| strcmp(readingPluginName, "Use main plugin") == 0)
	{
 		// Storage plugin and reading plugin are the same, or we have been 
		// explicitly told to use the storage plugin for reading so no need
		// to add a reading plugin
		return true;
	}
	if (plugin == NULL)
	{
		logger->error("Unable to fetch reading plugin name from configuration.\n");
		return false;
	}
	logger->info("Load reading plugin %s.", readingPluginName);
	string rpname = readingPluginName;
	if ((handle = manager->loadPlugin(rpname, PLUGIN_TYPE_STORAGE)) != NULL)
	{
		readingPlugin = new StoragePlugin(rpname, handle);
		if ((storagePlugin->getInfo()->options & SP_READINGS) == 0)
		{
			logger->error("Defined readings storage plugin %s does not support readings operations.\n",
					readingPluginName);
			return false;
		}
		api->setReadingPlugin(readingPlugin);
		logger->info("Loaded reading plugin %s.", readingPluginName);
	}
	else
	{
		return false;
	}
	return true;
}

/**
 * Shutdown request
 */
void StorageService::shutdown()
{
	/* Stop recieving new requests and allow existing
	 * requests to drain.
	 */
	m_shutdown = true;
	logger->info("Storage service shutdown in progress.");
	api->stopServer();

}

/**
 * Restart request
 */
void StorageService::restart()
{
	/* Stop recieving new requests and allow existing
	 * requests to drain.
	 */
	m_shutdown = true;
	logger->info("Storage service shutdown in progress.");
	api->stopServer();

}

/**
 * Configuration change notification
 */
void StorageService::configChange(const string& categoryName, const string& category)
{
	logger->info("Configuration category change '%s'", categoryName.c_str());
	if (!categoryName.compare(STORAGE_CATEGORY))
	{
		config->updateCategory(category);

		if (m_logLevel.compare(config->getValue("logLevel")))
		{
			m_logLevel = config->getValue("logLevel");
			logger->setMinLevel(m_logLevel);
		}
		if (config->hasValue("timeout"))
		{
			long timeout = strtol(config->getValue("timeout"), NULL, 10);
			if (timeout != m_timeout)
			{
				api->setTimeout(timeout);
				m_timeout = timeout;
			}
		}
		if (config->hasValue("perfmon"))
                {
			string perf = config->getValue("perfmon");
			if (perf.compare("true") == 0)
			{
				api->getPerformanceMonitor()->setCollecting(true);
			}
			else
			{
				api->getPerformanceMonitor()->setCollecting(false);
			}
		}
		return;
	}
	if (!categoryName.compare(getPluginName()))
	{
		storagePlugin->getConfig()->updateCategory(category);
		return;
	}
	if (config->hasValue("readingPlugin"))
	{
		const char *readingPluginName = config->getValue("readingPlugin");
		if (!categoryName.compare(readingPluginName))
		{
			readingPlugin->getConfig()->updateCategory(category);
		}
	}
}

/**
 * Return the name of the configured storage service
 */
string StorageService::getPluginName()
{
	return string(config->getValue("plugin"));
}

/**
 * Return the managed status of the storage plugin
 */
string StorageService::getPluginManagedStatus()
{
	return string(config->getValue("managedStatus"));
}

/**
 * Return the name of the configured reading plugin
 */
string StorageService::getReadingPluginName()
{
	string rval = config->getValue("readingPlugin");
	if (rval.empty())
	{
		rval = config->getValue("plugin");
	}
	return rval;
}

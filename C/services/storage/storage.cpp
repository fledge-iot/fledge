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

#define NO_EXIT_STACKTRACE		0		// Set to 1 to make storage loop after stacktrace

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
		else if (!strncmp(argv[i], "--logLevel=", 11))
		{
			logLevel = &argv[i][11];
		}
	}

	if (returnPlugin == false && daemonMode && makeDaemon() == -1)
	{
		// Failed to run in daemon mode
		cout << "Failed to run as deamon - proceeding in interactive mode." << endl;
	}

	StorageService *service = new StorageService(myName);
	Logger::getLogger()->setMinLevel(logLevel);
	if (returnPlugin)
	{
		cout << service->getPluginName() << " " << service->getPluginManagedStatus() << endl;
	}
	else
	{
		service->start(coreAddress, corePort);
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
	(void)dup(0);  			// stdout	GCC bug 66425 produces warning
	(void)dup(0);  			// stderr	GCC bug 66425 produces warning
 	return 0;
}

/**
 * Constructor for the storage service
 */
StorageService::StorageService(const string& myName) : m_name(myName),
						readingPlugin(NULL), m_shutdown(false)
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
	if (config->hasValue("logLevel"))
	{
		logger->setMinLevel(config->getValue("logLevel"));
	}
	else
	{
		logger->setMinLevel("warning");
	}


	api = new StorageApi(servicePort, threads);
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

		// Add the default configuration under the Advanced category
		unsigned int retryCount = 0;
		DefaultConfigCategory *conf = config->getDefaultCategory();
		conf->setDescription(CATEGORY_DESCRIPTION);
		while (client->addCategory(*conf, true) == false && ++retryCount < 10)
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

		// Regsiter for configuration changes to our category
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

			// Regsiter for configuration changes to our category
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

					// Regsiter for configuration changes to our category
					ConfigHandler *configHandler = ConfigHandler::getInstance(client);
					configHandler->registerCategory(this, conf->getName());
				}
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
 * @return bool	True if the plugins have been l;oaded and support the correct operations
 */
bool StorageService::loadPlugin()
{
	PluginManager *manager = PluginManager::getInstance();

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
 * Configuration change notification
 */
void StorageService::configChange(const string& categoryName, const string& category)
{
	logger->info("Configuration category change '%s'", categoryName.c_str());
	if (!categoryName.compare(STORAGE_CATEGORY))
	{
		config->updateCategory(category);
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

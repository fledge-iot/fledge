/*
 * FogLAMP process class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <sending.h>
#include <csignal>

// historian plugin to load
#define PLUGIN_NAME "omf"

// The type of the plugin managed by the Sending Process
#define PLUGIN_TYPE "north"

#define GLOBAL_CONFIG_KEY "GLOBAL_CONFIGURATION"
#define PLUGIN_CONFIG_KEY "PLUGIN"
#define PLUGIN_TYPES_KEY "OMF_TYPES"

// Configuration retrieved from the Configuration Manager
#define CONFIG_CATEGORY_NAME "SEND_PR_"
#define CONFIG_CATEGORY_DESCRIPTION "Configuration of the Sending Process"
#define CATEGORY_OMF_TYPES_DESCRIPTION "Configuration of OMF types"

using namespace std;

static map<string, string> globalConfiguration = {};

// Sending process default configuration
static const string sendingDefaultConfig =
	"\"enable\": {"
		"\"description\": \"A switch that can be used to enable or disable execution of "
			"the sending process.\", \"type\": \"boolean\", \"default\": \"True\" },"
       	"\"duration\": {"
            	"\"description\": \"How long the sending process should run (in seconds) before stopping.\", "
            	"\"type\": \"integer\", \"default\": \"60\" }, "
        "\"source\": {"
		"\"description\": \"Defines the source of the data to be sent on the stream, "
		"this may be one of either readings, statistics or audit.\", \"type\": \"string\", "
		"\"default\": \"readings\" }, "
	"\"blockSize\": {"
		"\"description\": \"The size of a block of readings to send in each transmission.\", "
		"\"type\": \"integer\", \"default\": \"500\" }, "
	"\"sleepInterval\": {"
		"\"description\": \"A period of time, expressed in seconds, "
			"to wait between attempts to send readings when there are no "
			"readings to be sent.\", \"type\": \"integer\", \"default\": \"1\" }, "
	"\"north\": {"
		"\"description\": \"The name of the north to use to translate the readings "
			"into the output format and send them\", \"type\": \"string\", "
			"\"default\": \"omf\" }, "
	"\"stream_id\": {"
		"\"description\": \"Stream ID\", \"type\": \"integer\", \"default\": \"1\" }";

volatile std::sig_atomic_t signalReceived = 0;

// Handle Signals
static void signalHandler(int signal)
{
  signalReceived = signal;
}

/**
 * SendingProcess class methods
 */

// Destructor
SendingProcess::~SendingProcess()
{
	delete m_thread_load;
	delete m_thread_send;
	delete m_plugin;
}

// SendingProcess Class Constructor
SendingProcess::SendingProcess(int argc, char** argv) : FogLampProcess(argc, argv)
{
	// Get streamID from command line
	m_stream_id = atoi(this->getArgValue("--stream-id=").c_str());

	// Set buffer of ReadingSet with NULLs
	m_buffer.resize(DATA_BUFFER_ELMS, NULL);

	// Mark running state
	m_running = true;

	// NorthPlugin
	m_plugin = NULL;

	// Set vars & counters to 0, false
	m_last_sent_id  = 0;
	m_tot_sent = 0;
	m_update_db = false;

	Logger::getLogger()->info("SendingProcess is starting, stream id = %d", m_stream_id);

        if (!loadPlugin(string(PLUGIN_NAME)))
	{
		string errMsg("SendingProcess: failed to load north plugin '");
		errMsg.append(PLUGIN_NAME);
		errMsg += "'.";

		Logger::getLogger()->fatal(errMsg.c_str());

		throw runtime_error(errMsg);
	}

	/**
	 * Get Configuration from sending process and loaed plugin
	 * Create or update configuration via FogLAMP API
	 */
	const map<string, string>& config = this->fetchConfiguration();

	// Init plugin with merged configuration from FogLAMP API
	this->m_plugin->init(config);

	// Fetch last_object sent from foglamp.streams
	if (!this->getLastSentReadingId())
	{
		string errMsg("Last object id for stream '");
		errMsg.append(to_string(m_stream_id));
		errMsg += "' NOT found.";

		Logger::getLogger()->fatal(errMsg.c_str());
		throw runtime_error(errMsg);
	}

	Logger::getLogger()->info("SendingProcess initialised with %d data buffers.",
				  DATA_BUFFER_ELMS);

	Logger::getLogger()->info("SendingProcess reads data from last id %lu",
				  this->getLastSentId());
}

// While running check signals and execution time
void SendingProcess::run() const
{
	// We handle these signals, add more if needed
	std::signal(SIGINT,  signalHandler);
	std::signal(SIGSTOP, signalHandler);
	std::signal(SIGTERM, signalHandler);

	// Check running time
	time_t elapsedSeconds = 0;
	while (elapsedSeconds < (time_t)m_duration)
	{
		// Check whether a signal has been received
		if (signalReceived != 0)
		{
			Logger::getLogger()->info("SendingProcess is stopping due to caught signal %d (%s)",
						  signalReceived,
						  strsignal(signalReceived),
						  elapsedSeconds);
			break;
		}

		// Just sleep
		sleep(m_sleep);

		elapsedSeconds = time(NULL) - this->getStartTime();
	}
	Logger::getLogger()->info("SendingProcess is stopping, after %d seconds.",
				  elapsedSeconds);
}

/**
 * Load the Historian specific 'transform & send data' plugin
 *
 * @param    pluginName    The plugin to load
 * @return   true if loded, false otherwise 
 */
bool SendingProcess::loadPlugin(const string& pluginName)
{
        PluginManager *manager = PluginManager::getInstance();

        if (pluginName.empty())
        {
                Logger::getLogger()->error("Unable to fetch north plugin '%s' from configuration.", pluginName);
                return false;
        }
        Logger::getLogger()->info("Load north plugin '%s'.", pluginName.c_str());

        PLUGIN_HANDLE handle;

        if ((handle = manager->loadPlugin(pluginName, PLUGIN_TYPE_NORTH)) != NULL)
        {
                Logger::getLogger()->info("Loaded north plugin '%s'.", pluginName.c_str());
                m_plugin = new NorthPlugin(handle);
                return true;
        }
        return false;
}

// Stop running threads & cleanup used resources
void SendingProcess::stop()
{
	// End of processing loop for threads
	this->stopRunning();

	// Threads execution has completed.
	this->m_thread_load->join();
        this->m_thread_send->join();

	// Remove the data buffers
	for (unsigned int i = 0; i < DATA_BUFFER_ELMS; i++)
	{
		ReadingSet* data = this->m_buffer[i];
		if (data != NULL)
		{
			delete data;
		}
	}

	// Cleanup the plugin resources
	this->m_plugin->shutdown();

	Logger::getLogger()->info("SendingProcess succesfully terminated");
}

/**
 * Update datbaase tables statistics and streams
 * setting last_object id in streams
 * and numReadings sent in statistics
 */
void SendingProcess::updateDatabaseCounters()
{
	// Update counters to Database

	string streamId = to_string(this->getStreamId());

	// Prepare WHERE id = val
	const Condition conditionStream(Equals);
	Where wStreamId("id",
			conditionStream,
			streamId);

	// Prepare last_object = value
	InsertValues lastId;
	lastId.push_back(InsertValue("last_object",
			 (long)this->getLastSentId()));

	// Perform UPDATE foglamp.streams SET last_object = x WHERE id = y
	this->getStorageClient()->updateTable("streams",
					      lastId,
					      wStreamId);

	// Prepare "WHERE SENT_x = val
	const Condition conditionStat(Equals);
	Where wLastStat("key",
			conditionStat,
			string("SENT_" + streamId));

	// Prepare value = value + inc
	ExpressionValues updateValue;
	updateValue.push_back(Expression("value",
			      "+",
			      (int)this->getSentReadings()));

	// Perform UPDATE foglamp.statistics SET value = value + x WHERE key = 'y'
	this->getStorageClient()->updateTable("statistics",
					      updateValue,
					      wLastStat);
}

/**
 * Get last_object id sent for current stream_id
 * Access foglam.streams table.
 *
 * @return true if last_object is found, false otherwise
 */
bool SendingProcess::getLastSentReadingId()
{
	// Fetch last_object sent from foglamp.streams

	bool foundId = false;
	const Condition conditionId(Equals);
	string streamId = to_string(this->getStreamId());
	Where* wStreamId = new Where("id",
				     conditionId,
				     streamId);

	// SELECT * FROM foglamp.streams WHERE id = x
	Query qLastId(wStreamId);

	ResultSet* lastObjectId = this->getStorageClient()->queryTable("streams", qLastId);

	if (lastObjectId != NULL && lastObjectId->rowCount())
	{
		// Get the first row only
		ResultSet::RowIterator it = lastObjectId->firstRow();
		// Access the element
		ResultSet::Row* row = *it;
		if (row)
		{
			// Get column value
			ResultSet::ColumnValue* theVal = row->getColumn("last_object");
			// Set found id
			this->setLastSentId((unsigned long)theVal->getInteger());

			foundId = true;
		}
	}

	return foundId;
}

/**
 * Create or Update the sending process configuration
 * by accessing FogLAMP rest API service
 *
 * SendingProcess + plugin DEFAULT configuration is passed to
 * configuration manager and a merged one with "value" and "default"
 * is returned.
 *
 * Return the configuration items as a map of JSON strings
 */
const map<string, string>& SendingProcess::fetchConfiguration()
{
	string catName(CONFIG_CATEGORY_NAME + to_string(this->getStreamId()));

	// Build JSON merged configuration (sendingProcess + pluginConfig
	string config("{ ");
	config.append(this->m_plugin->config()[string(PLUGIN_CONFIG_KEY)]);
	config += ", ";
	config.append(sendingDefaultConfig);
	config += " }";

	try
	{
		// Create category, with "default" values only 
		DefaultConfigCategory category(catName, config);
		category.setDescription(CONFIG_CATEGORY_DESCRIPTION);

		if (!this->getManagementClient()->addCategory(category))
		{
			string errMsg("Failure creating/updating configuration key '");
			errMsg.append(catName);
			errMsg += "'";

			Logger::getLogger()->fatal(errMsg.c_str());
			throw runtime_error(errMsg);
		}

		// Create types category, with "default" values only 
		string configTypes("{ ");
		configTypes.append(this->m_plugin->config()[string(PLUGIN_TYPES_KEY)]);
		configTypes += " }";

		DefaultConfigCategory types(string(PLUGIN_TYPES_KEY), configTypes);
		category.setDescription(CATEGORY_OMF_TYPES_DESCRIPTION);

		if (!this->getManagementClient()->addCategory(types))
		{
			string errMsg("Failure creating/updating configuration key '");
			errMsg.append(PLUGIN_TYPES_KEY);
			errMsg += "'";

			Logger::getLogger()->fatal(errMsg.c_str());
			throw runtime_error(errMsg);
		}

		// Get the category with values and defaults
		ConfigCategory sendingProcessConfig = this->getManagementClient()->getCategory(catName);

		// Get the category with values and defaults for OMF_TYPES
		ConfigCategory pluginTypes = this->getManagementClient()->getCategory(string(PLUGIN_TYPES_KEY));

		/**
		 * Handle the sending process parameters here
		 */

		string blockSize = sendingProcessConfig.getValue("blockSize");
		string duration = sendingProcessConfig.getValue("duration");
		string sleepInterval = sendingProcessConfig.getValue("sleepInterval");

                // Set member variables
		m_block_size = strtoul(blockSize.c_str(), NULL, 10);
		m_sleep = strtoul(sleepInterval.c_str(), NULL, 10);
		m_duration = strtoul(duration.c_str(), NULL, 10);

		Logger::getLogger()->info("SendingProcess configuration parameters: blockSize=%d, "
					  "duration=%d, sleepInterval=%d",
					  m_block_size,
					  m_duration,
					  m_sleep);

		globalConfiguration[string(GLOBAL_CONFIG_KEY)] = sendingProcessConfig.itemsToJSON();
		globalConfiguration[string(PLUGIN_TYPES_KEY)] = pluginTypes.itemsToJSON();

		// Return both values & defaults for config items only
		return globalConfiguration;
	}
	catch (std::exception* e)
	{
		return globalConfiguration;
	}
	catch (...)
	{
		return globalConfiguration;
	}
}

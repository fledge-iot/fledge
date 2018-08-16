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
#include <sys/prctl.h>
#include <filter_plugin.h>

#define PLUGIN_UNDEFINED ""

// The type of the plugin managed by the Sending Process
#define PLUGIN_TYPE "north"

#define GLOBAL_CONFIG_KEY "GLOBAL_CONFIGURATION"
#define PLUGIN_CONFIG_KEY "PLUGIN"
#define PLUGIN_TYPES_KEY "OMF_TYPES"

// Configuration retrieved from the Configuration Manager
#define CONFIG_CATEGORY_DESCRIPTION "Configuration of the Sending Process"
#define CATEGORY_OMF_TYPES_DESCRIPTION "Configuration of OMF types"

// Default values for the creation of a new stream,
// the description is derived from the parameter --name
#define NEW_STREAM_DESTINATION 1
#define NEW_STREAM_LAST_OBJECT 0

using namespace std;

// static pointer to data buffers for filter plugins
std::vector<ReadingSet*>* SendingProcess::m_buffer_ptr = 0;

// Used to identifies logs
const string LOG_SERVICE_NAME = "SendingProcess/sending";

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
	"\"streamId\": {"
		"\"description\": \"Identifies the specific stream to handle and the related information,"
		" among them the ID of the last object streamed.\", \"type\": \"integer\", \"default\": \"0\" }";


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
        m_logger = Logger::getLogger();

	// the stream_id to use is retrieved from the configuration
        m_stream_id = -1;
	m_plugin_name = PLUGIN_UNDEFINED;

        int i;
        for (i = 0; i < argc; i++)
        {
                m_logger->debug("%s - param :%d: :%s:",
				LOG_SERVICE_NAME.c_str(),
				i,
				argv[i]);
        }

        // Set buffer of ReadingSet with NULLs
	m_buffer.resize(DATA_BUFFER_ELMS, NULL);
	// Set the static pointer
	m_buffer_ptr = &m_buffer;

	// Mark running state
	m_running = true;

	// NorthPlugin
	m_plugin = NULL;

	// Set vars & counters to 0, false
	m_last_sent_id  = 0;
	m_tot_sent = 0;
	m_update_db = false;

	Logger::getLogger()->info("SendingProcess is starting");

	/**
	 * Get Configuration from sending process and loaded plugin
	 * Create or update configuration via FogLAMP API
	 */

	// Reads the sending process configuration
	this->fetchConfiguration(sendingDefaultConfig,
				 PLUGIN_UNDEFINED);

        if (m_plugin_name == PLUGIN_UNDEFINED) {

                // Ends the execution if the plug-in is not defined

                string errMsg(LOG_SERVICE_NAME + " - the plugin-in is not defined for the sending process :" +  this->getName() + " :.");

                m_logger->fatal(errMsg);
                throw runtime_error(errMsg);
        }

        // Loads the plug-in
        if (!loadPlugin(string(m_plugin_name)))
        {
                string errMsg("SendingProcess: failed to load north plugin '");
                errMsg.append(m_plugin_name);
                errMsg += "'.";

                Logger::getLogger()->fatal(errMsg);

                throw runtime_error(errMsg);
        }

        // Reads the sending process configuration merged with the ones related to the loaded plugin
        const map<string, string>& config = this->fetchConfiguration(sendingDefaultConfig,
                                                                     m_plugin_name);

        m_logger->debug("%s - stream-id :%d:", LOG_SERVICE_NAME.c_str() , m_stream_id);

        // Checks if stream-id is undefined, it allocates a new one in the case
        if (m_stream_id == 0) {

                m_logger->info("%s - stream-id is undefined, allocating a new one.",
			       LOG_SERVICE_NAME.c_str());

                m_stream_id = this->createNewStream();

                if (m_stream_id == 0) {

			string errMsg(LOG_SERVICE_NAME + " - it is not possible to create a new stream.");

			m_logger->fatal(errMsg);
			throw runtime_error(errMsg);
		} else {
			m_logger->info("%s - new stream-id allocated :%d:",
				       LOG_SERVICE_NAME.c_str(),
				       m_stream_id);

                        const string categoryName = this->getName();
                        const string itemName = "streamId";
                        const string itemValue = to_string(m_stream_id);

                        // Prepares the error message in case of an error
                        string errMsg(LOG_SERVICE_NAME + " - it is not possible to update the item :" + itemName + " : of the category :" + categoryName + ":");

                        try {
                                this->getManagementClient()->setCategoryItemValue(categoryName,
                                                                                  itemName,
                                                                                  itemValue);

                                m_logger->info("%s - configuration updated, using stream-id :%d:",
					       LOG_SERVICE_NAME.c_str(),
					       m_stream_id);

                        } catch (std::exception* e) {

                                delete e;

                                m_logger->error(errMsg);
                                throw runtime_error(errMsg);

                        } catch (...) {
                                m_logger->fatal(errMsg);
                                throw runtime_error(errMsg);
                        }
                }
        }

        // Init plugin with merged configuration from FogLAMP API
	this->m_plugin->init(config);

	// Fetch last_object sent from foglamp.streams
	if (!this->getLastSentReadingId())
	{
                m_logger->warn(LOG_SERVICE_NAME + " - Last object id for stream '" + to_string(m_stream_id) + "' NOT found, creating a new stream.");

		if (!this->createStream(m_stream_id)) {

			string errMsg(LOG_SERVICE_NAME + " - It is not possible to create a new stream for streamId :" + to_string(m_stream_id) + ":.");

                        m_logger->fatal(errMsg);
			throw runtime_error(errMsg);
		} else {
                        m_logger->info(LOG_SERVICE_NAME + " - streamId :" + to_string(m_stream_id) + ": created.");
		}
	}

	Logger::getLogger()->info("SendingProcess initialised with %d data buffers.",
				  DATA_BUFFER_ELMS);

	Logger::getLogger()->info("SendingProcess data source type is '%s'",
				  this->getDataSourceType().c_str());

	Logger::getLogger()->info("SendingProcess reads data from last id %lu",
				  this->getLastSentId());

	// Load filter plugins
	if (!this->loadFilters(this->getName()))
	{
		Logger::getLogger()->fatal("SendingProcess failed loading filter plugins. Exiting");
		throw runtime_error(LOG_SERVICE_NAME + " failure while loading filter plugins.");
	}
}

// While running check signals and execution time
void SendingProcess::run() const
{

        // Requests the kernel to deliver SIGHUP when parent dies
        prctl(PR_SET_PDEATHSIG, SIGHUP);

	// We handle these signals, add more if needed
        std::signal(SIGHUP,  signalHandler);
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
                Logger::getLogger()->error("Unable to fetch north plugin '%s' from configuration.",
					   pluginName.c_str());
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

	// Cleanup filters
	if (m_filters.size())
	{
		FilterPlugin::cleanupFilters(m_filters);
	}

	Logger::getLogger()->info("SendingProcess successfully terminated");
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

	// Prepare foglamp.statistics update
	string statistics_key = this->getName();
	for (auto & c: statistics_key) c = toupper(c);

	// Prepare "WHERE key = name
	const Condition conditionStat(Equals);
	Where wLastStat("key",
			conditionStat,
                        statistics_key);

	// Prepare value = value + inc
	ExpressionValues updateValue;
	updateValue.push_back(Expression("value",
			      "+",
			      (int)this->getSentReadings()));

	// Perform UPDATE foglamp.statistics SET value = value + x WHERE key = 'name'
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
	// Free result set
	delete lastObjectId;

	return foundId;
}

/**
 * Creates a new stream, it adds a new row into the streams table allocating a new stream id
 *
 * @return newly created stream, 0 otherwise
 */
int SendingProcess::createNewStream()
{
        int streamId = 0;

        InsertValues streamValues;
        streamValues.push_back(InsertValue("destination_id", NEW_STREAM_DESTINATION));
        streamValues.push_back(InsertValue("description",    this->getName()));
        streamValues.push_back(InsertValue("last_object",    NEW_STREAM_LAST_OBJECT));

        if (getStorageClient()->insertTable("streams", streamValues) != 1) {

                getLogger()->error("Failed to insert a row into the streams table");

        } else {

                // Select the row just created, having description='process name'
                const Condition conditionId(Equals);
                string name  = getName();
                Where* wName = new Where("description", conditionId, name);
                Query qName(wName);

                ResultSet* rows = this->getStorageClient()->queryTable("streams", qName);

                if (rows != NULL && rows->rowCount())
                {
                        // Get the first row only
                        ResultSet::RowIterator it = rows->firstRow();
                        // Access the element
                        ResultSet::Row* row = *it;
                        if (row)
                        {
                                // Get column value
                                ResultSet::ColumnValue* theVal = row->getColumn("id");
                                streamId = (int)theVal->getInteger();
                        }
                }

        }

        return streamId;
}

/**
 * Creates a new stream, it adds a new row into the streams table allocating specific stream id
 *
 * @return true if successful created, false otherwise
 */
bool SendingProcess::createStream(int streamId)
{
	bool created = false;

	InsertValues streamValues;
	streamValues.push_back(InsertValue("id",             streamId));
	streamValues.push_back(InsertValue("destination_id", NEW_STREAM_DESTINATION));
	streamValues.push_back(InsertValue("description",    this->getName()));
	streamValues.push_back(InsertValue("last_object",    NEW_STREAM_LAST_OBJECT));

        if (getStorageClient()->insertTable("streams", streamValues) != 1) {

		getLogger()->error("Failed to insert a row into the streams table for the streamId :%d:" ,streamId);

	} else {
		created = true;

		// Set initial last_object
		this->setLastSentId((unsigned long) NEW_STREAM_LAST_OBJECT);
	}

	return created;
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
const map<string, string>& SendingProcess::fetchConfiguration(const std::string& defaultConfig,
							      const std::string&  plugin_name)
{

	// retrieves the configuration using the value of the --name parameter (received in the command line) as the key
	string catName(this->getName());
	Logger::getLogger()->debug("%s - catName :%s:", LOG_SERVICE_NAME.c_str(), catName.c_str());

	// Build JSON merged configuration (sendingProcess + pluginConfig
	string config("{ ");

	if (plugin_name != PLUGIN_UNDEFINED) {

		config.append(this->m_plugin->config()[string(PLUGIN_CONFIG_KEY)]);
		config += ", ";
	}
	config.append(defaultConfig);
	config += " }";

	try
	{
		// Create category, with "default" values only 
		DefaultConfigCategory category(catName, config);
		category.setDescription(CONFIG_CATEGORY_DESCRIPTION);

		if (!this->getManagementClient()->addCategory(category, true))
		{
			string errMsg("Failure creating/updating configuration key '");
			errMsg.append(catName);
			errMsg += "'";

			Logger::getLogger()->fatal(errMsg.c_str());
			throw runtime_error(errMsg);
		}

		bool plugin_types_key_present = false;

		if (plugin_name != PLUGIN_UNDEFINED) {

			const map<const string, const string>& plugin_cfg_map = this->m_plugin->config();
			if (plugin_cfg_map.find(string(PLUGIN_TYPES_KEY)) != plugin_cfg_map.end()) {
				plugin_types_key_present = true;
				// Create types category, with "default" values only
				string configTypes("{ ");
				configTypes.append(this->m_plugin->config()[string(PLUGIN_TYPES_KEY)]);
				configTypes += " }";

				DefaultConfigCategory types(string(PLUGIN_TYPES_KEY), configTypes);
				category.setDescription(CATEGORY_OMF_TYPES_DESCRIPTION);  // should be types.setDescription?

				if (!this->getManagementClient()->addCategory(types, true)) {
					string errMsg("Failure creating/updating configuration key '");
					errMsg.append(PLUGIN_TYPES_KEY);
					errMsg += "'";

					Logger::getLogger()->fatal(errMsg.c_str());
					throw runtime_error(errMsg);
				}
			}
			else
				Logger::getLogger()->debug("Key '%s' missing from plugin config map (required for OMF north plugin only at the moment)", PLUGIN_TYPES_KEY);
		}

		// Get the category with values and defaults
		ConfigCategory sendingProcessConfig = this->getManagementClient()->getCategory(catName);
		ConfigCategory pluginTypes;

		if (plugin_name != PLUGIN_UNDEFINED && plugin_types_key_present) {

			// Get the category with values and defaults for OMF_TYPES
			pluginTypes = this->getManagementClient()->getCategory(string(PLUGIN_TYPES_KEY));
		}

		/**
		 * Handle the sending process parameters here
		 */

		string blockSize = sendingProcessConfig.getValue("blockSize");
		string duration = sendingProcessConfig.getValue("duration");
		string sleepInterval = sendingProcessConfig.getValue("sleepInterval");

                // Handles the case in which the stream_id is not defined in the configuration
                // and sets it to not defined (0)
                string streamId = "";
                try {
                        streamId = sendingProcessConfig.getValue("streamId");
                } catch (std::exception* e) {

                        delete e;
                        streamId = "0";
                } catch (...) {
                        streamId = "0";
                }

                // sets to undefined if not defined in the configuration
                try {
                        m_plugin_name = sendingProcessConfig.getValue("plugin");
                } catch (std::exception* e) {

                        delete e;
                        m_plugin_name = PLUGIN_UNDEFINED;
                } catch (...) {
                        m_plugin_name = PLUGIN_UNDEFINED;
                }

		/**
		 * Set member variables
		 */
		m_block_size = strtoul(blockSize.c_str(), NULL, 10);
		m_sleep = strtoul(sleepInterval.c_str(), NULL, 10);
		m_duration = strtoul(duration.c_str(), NULL, 10);
                m_stream_id = atoi(streamId.c_str());
		// Set the data source type: readings (default) or statistics
		m_data_source_t = sendingProcessConfig.getValue("source");

		Logger::getLogger()->info("SendingProcess configuration parameters: pluginName=%s, blockSize=%d, "
					  "duration=%d, sleepInterval=%d, streamId=%d",
					  plugin_name.c_str(),
					  m_block_size,
					  m_duration,
					  m_sleep,
                                          m_stream_id);

		globalConfiguration[string(GLOBAL_CONFIG_KEY)] = sendingProcessConfig.itemsToJSON();

		if (plugin_name != PLUGIN_UNDEFINED && plugin_types_key_present) {
			globalConfiguration[string(PLUGIN_TYPES_KEY)] = pluginTypes.itemsToJSON();
		}

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

/**
 * Load filter plugins for the given configuration
 *
 * @param categoryName	The sending process category name
 * @return 		True if filters were loaded and initialised
 *			or there are no filters
 *			False with load/init errors
 */
bool SendingProcess::loadFilters(const string& categoryName)
{
	// Try to load filters:
	if (!FilterPlugin::loadFilters(categoryName,
				       m_filters,
				       this->getManagementClient()))
	{
		// return false on any error
		return false;
	}

	// return true if no filters
	if (m_filters.size() == 0)
	{
		return true;
	}

	// We have some filters: set up the filter pipeline
	return this->setupFiltersPipeline();
}

/**
 * Use the current input readings (they have been filtered
 * by all filters)
 *
 * Note:
 * This routine must passed to last filter "plugin_init" only
 *
 * Static method
 *
 * @param outHandle	Pointer to current buffer index
 *			where to add the readings
 * @param readings	Filtered readings to add to buffer[index]
 */ 	
void SendingProcess::useFilteredData(OUTPUT_HANDLE *outHandle,
				     READINGSET *readings)
{
	// Handle the readings set by adding readings set to data buffer[index]
	unsigned long* loadBufferIndex = (unsigned long *)outHandle;
	SendingProcess::getDataBuffers()->at(*loadBufferIndex) = (ReadingSet *)readings;
}

/**
 * Pass the current readings set to the next filter in the pipeline
 *
 * Note:
 * This routine must be passed to all filters "plugin_init" except the last one
 *
 * Static method
 *
 * @param outHandle	Pointer to next filter
 * @param readings	Current readings set
 */ 	
void SendingProcess::passToOnwardFilter(OUTPUT_HANDLE *outHandle,
					READINGSET *readings)
{
	// Get next filter in the pipeline
	FilterPlugin *next = (FilterPlugin *)outHandle;
	// Pass readings to next filter
	next->ingest(readings);
}

/**
 * Set the current buffer load index
 *
 * @param loadBufferIndex    The buffer load index the load thread is using
 */
void SendingProcess::setLoadBufferIndex(unsigned long loadBufferIndex)
{
	m_load_buffer_index = loadBufferIndex;
}

/**
 * Get the current buffer load index
 *
 * @return	The buffer load index the load thread is using
 */
unsigned long SendingProcess::getLoadBufferIndex() const
{
        return m_load_buffer_index;
}

/**
 * Get the current buffer load index pointer
 *
 * NOTE:
 * this routine must be called only to pass the index pointer
 * to the last filter in the pipeline for the readings set.
 *
 * @return    The pointer to the buffer load index being used by the load thread
 */
const unsigned long* SendingProcess::getLoadBufferIndexPtr() const
{
        return &m_load_buffer_index;
}

/**
 * Setup the filters pipeline
 *
 * This routine is calles when there are loaded filters.
 *
 * Set up the filter pipeline
 * by calling the "plugin_init" method with the right OUTPUT_HANDLE function
 * and OUTPUT_HANDLE pointer
 *
 * @return 		True on success,
 *			False otherwise.
 * @thown		Any caught exception
 */
bool SendingProcess::setupFiltersPipeline() const
{
	bool initErrors = false;
	string errMsg = "'plugin_init' failed for filter '";

	for (auto it = m_filters.begin(); it != m_filters.end(); ++it)
	{
		string filterCategoryName = this->getName();
		filterCategoryName.append("_");
		filterCategoryName += (*it)->getName();
		filterCategoryName.append("Filter");

		ConfigCategory updatedCfg;
		vector<string> children;

		try
		{
			// Fetch up to date filter configuration
			updatedCfg = this->getManagementClient()->getCategory(filterCategoryName);

			// Add filter category name under service/process config name
			children.push_back(filterCategoryName);
			this->getManagementClient()->addChildCategories(this->getName(), children);
		}
		// TODO catch specific exceptions
		catch (...)
		{
			throw;
		}

		if ((it + 1) != m_filters.end())
		{
			// Set next filter pointer as OUTPUT_HANDLE
			if (!(*it)->init(updatedCfg,
				    (OUTPUT_HANDLE *)(*(it + 1)),
				    this->passToOnwardFilter))
			{
				errMsg += (*it)->getName() + "'";
				initErrors = true;
				break;
			}
		}
		else
		{
			// Set load buffer index pointer as OUTPUT_HANDLE
			const unsigned long* bufferIndex = this->getLoadBufferIndexPtr();
			if (!(*it)->init(updatedCfg,
				    (OUTPUT_HANDLE *)(bufferIndex),
				    this->useFilteredData))
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
		m_logger->fatal("%s error: %s",
				LOG_SERVICE_NAME,
				errMsg.c_str());
		return false;
	}

	//Success
	return true;
}

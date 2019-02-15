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
#include <condition_variable>
#include <reading_set.h>
#include <plugin_manager.h>
#include <plugin_api.h>
#include <plugin.h>

#define VERBOSE_LOG	0

/**
 * The sending process is run according to a schedule in order to send reading data
 * to the historian, e.g. the PI system.
 * It’s role is to implement the rules as to what needs to be sent and when,
 * extract the data from the storage subsystem and stream it to the north
 * for sending to the external system.
 * The sending process does not implement the protocol used to send the data,
 * that is devolved to the translation plugin in order to allow for flexibility
 * in the translation process.
 */

#define TASK_FETCH_SLEEP 500
#define TASK_SEND_SLEEP 500
#define TASK_SLEEP_MAX_INCREMENTS 7 // from 0,5 secs to up to 32 secs

using namespace std;
using namespace std::chrono;

// Mutex for m_buffer access
mutex      readMutex;
// Mutex for thread idle time
mutex	waitMutex;
// Block the calling thread until notified to resume.
condition_variable cond_var;

// Buffer max elements
unsigned long memoryBufferSize;

// Exit code:
// 0 = success (some data sent)
// 1 = 100% failure sending data to north server
// 2 =internal errors
int exitCode = 1;

// Used to identifies logs
const string LOG_SERVICE_NAME = "SendingProcess/sending_process";

// Load data from storage
static void loadDataThread(SendingProcess *loadData);
// Send data from historian
static void sendDataThread(SendingProcess *sendData);

int main(int argc, char** argv)
{
	try
	{
                // Instantiate SendingProcess class
		SendingProcess sendingProcess(argc, argv);

		memoryBufferSize = sendingProcess.getMemoryBufferSize();

		// Launch the load thread
		sendingProcess.m_thread_load = new thread(loadDataThread, &sendingProcess);
		// Launch the send thread
		sendingProcess.m_thread_send = new thread(sendDataThread, &sendingProcess);

		// Run: max execution time or caught signals can stop it
		sendingProcess.run();

		// Unlock load & send threads
		cond_var.notify_all();

		// End processing
		sendingProcess.stop();
	}
	catch (const std::exception& e)
	{
		cerr << "Exception in " << argv[0] << " : " << e.what() << endl;
		// Return failure for class instance/configuration etc
		exit(2);
	}
	// Catch all exceptions
	catch (...)
	{
		std::exception_ptr p = std::current_exception();
		string name = (p ? p.__cxa_exception_type()->name() : "null");
		cerr << "Generic Exception in " << argv[0] << " : " << name << endl;
		exit(2);
	}

	// Return success
	exit(exitCode);
}

/**
 * Apply load filter
 *
 * Just call "ingest" methid of the first one
 *
 * @param loadData    pointer to SendingProcess instance
 * @param readingSet  The current reading set loaded from storage
 */
void applyFilters(SendingProcess* loadData,
		  ReadingSet* readingSet)
{
	// Get first filter
	FilterPlugin *firstFilter = loadData->filterPipeline->getFirstFilterPlugin();
	
	// Call first filter "ingest"
	// Note:
	// next filters will be automatically called
	if (firstFilter)
		firstFilter->ingest(readingSet);
}

/**
 * Thread to load data from the storage layer.
 *
 * @param loadData    pointer to SendingProcess instance
 */
static void loadDataThread(SendingProcess *loadData)
{
        unsigned int    readIdx = 0;

	// Read from the storage last Id already sent
	loadData->setLastFetchId(loadData->getLastSentId());

	while (loadData->isRunning())
        {
                if (readIdx >= memoryBufferSize)
                {
                        readIdx = 0;
                }

		/**
		 * Check whether m_buffer[readIdx] is NULL or contains a ReadingSet
		 *
		 * Access is protected by a mutex.
		 */
                readMutex.lock();
                ReadingSet *canLoad = loadData->m_buffer.at(readIdx);
                readMutex.unlock();

                if (canLoad)
                {
#if VERBOSE_LOG
			Logger::getLogger()->info("SendingProcess loadDataThread: "
						  "('%s' stream id %d), readIdx %u, buffer is NOT empty, waiting ...",
						  loadData->getDataSourceType().c_str(),
						  loadData->getStreamId(),
						  readIdx);
#endif

	                Logger::getLogger()->warn("SendingProcess is faster to load data than the destination to process them,"
	                                          " so all the %lu in memory buffers are full and the load thread should wait until at least a buffer is freed.",
	                                          loadData->getMemoryBufferSize());

	                if (loadData->isRunning()) {

				// Load thread is put on hold, only if the execution should proceed
				unique_lock<mutex> lock(waitMutex);
				cond_var.wait(lock);
			}
                }
                else
                {
                        // Load data from storage client (id >= lastId and getReadBlockSize() rows)
			ReadingSet* readings = NULL;
			try
			{
				bool isReading = !loadData->getDataSourceType().compare("statistics") ? false : true; 
				//high_resolution_clock::time_point t1 = high_resolution_clock::now();
				if (isReading)
				{
					// Read from storage all readings with id > last sent id
					unsigned long lastReadId = loadData->getLastFetchId() + 1;
					readings = loadData->getStorageClient()->readingFetch(lastReadId,
											      loadData->getReadBlockSize());
				}
				else
				{
					// SELECT id,
					//	  key AS asset_code,
					//	  key AS read_key,
					//	  ts,
					//	  history_ts AS user_ts,
					//	  value
					// FROM statistic_history
					// WHERE id > lastId
					// ORDER BY ID ASC
					// LIMIT blockSize
					const Condition conditionId(GreaterThan);
					// WHERE id > lastId
					Where* wId = new Where("id",
								conditionId,
								to_string(loadData->getLastFetchId()));
					vector<Returns *> columns;
					// Add colums and needed aliases
					columns.push_back(new Returns("id"));
					columns.push_back(new Returns("key", "asset_code"));
					columns.push_back(new Returns("key", "read_key"));
					columns.push_back(new Returns("ts"));

					Returns *tmpReturn = new Returns("history_ts", "user_ts");
					tmpReturn->timezone("utc");
					columns.push_back(tmpReturn);

					columns.push_back(new Returns("value"));
					// Build the query with fields, aliases and where
					Query qStatistics(columns, wId);
					// Set limit
					qStatistics.limit(loadData->getReadBlockSize());
					// Set sort
					Sort* sort = new Sort("id");
					qStatistics.sort(sort);

					// Query the statistics_history tbale and get a ReadingSet result
					readings = loadData->getStorageClient()->queryTableToReadings("statistics_history",
												      qStatistics);
				}
				//high_resolution_clock::time_point t2 = high_resolution_clock::now();
				//auto duration = duration_cast<microseconds>( t2 - t1 ).count();
			}
			catch (ReadingSetException* e)
			{
				Logger::getLogger()->error("SendingProcess loadData(): ReadingSet Exception '%s'", e->what());
			}
			catch (std::exception& e)
			{
				Logger::getLogger()->error("SendingProcess loadData(): Generic Exception: '%s'", e.what());
			}

			// Data fetched from storage layer
			if (readings != NULL && readings->getCount())
			{
				//Update last fetched reading Id
				loadData->setLastFetchId(readings->getLastId());

				/**
				 * Set last fetched reading Id for buffer index
				 * This is used by send thread whiule updating the next
				 * position to read from db.
				 * NOTE:
				 * The saved position is not ffected by the filters
				 * called below which can skip some or all input readings.
				 */
				loadData->m_last_read_id.at(readIdx) = readings->getLastId();

				/**
				 * The buffer access is protected by a mutex
				 */
                	        readMutex.lock();

				/**
				 * Set now the buffer at index to ReadingSet pointer
				 * Note: the ReadingSet pointer will be deleted by
				 * - the sending thread when processin it
				 * OR
				 * at program exit by a cleanup routine
				 *					
				 * Note: the readings set can be optionally filtered
				 * if plugin filters are set.
				 */

				// Apply filters to the reading set
				if (loadData->filterPipeline)
				{
					FilterPlugin *firstFilter = loadData->filterPipeline->getFirstFilterPlugin();
					if (firstFilter)
					{
						// Make the load readIdx available to filters
						loadData->setLoadBufferIndex(readIdx);
						// Apply filters
						applyFilters(loadData, readings);
					}
					else
					{
						// No filters: just set buffer with current data
						loadData->m_buffer.at(readIdx) = readings;
					}
				}
				else
				{
					// No filters: just set buffer with current data
					loadData->m_buffer.at(readIdx) = readings;
				}

				// Update asset tracker table/cache, if required
				vector<Reading *> *vec = loadData->m_buffer.at(readIdx)->getAllReadingsPtr();
				for (vector<Reading *>::iterator it = vec->begin(); it != vec->end(); ++it)
				{
					Reading *reading = *it;
					AssetTrackingTuple tuple(loadData->getName(), loadData->getPluginName(), reading->getAssetName(), "Egress");
					if (!AssetTracker::getAssetTracker()->checkAssetTrackingCache(tuple))
					{
						AssetTracker::getAssetTracker()->addAssetTrackingTuple(tuple);
						Logger::getLogger()->info("loadDataThread(): Adding new asset tracking tuple seen during readings' egress: %s", tuple.assetToString().c_str());
					}
				}

				readMutex.unlock();

				readIdx++;

				// Unlock the sendData thread
				unique_lock<mutex> lock(waitMutex);
				cond_var.notify_one();
			}
			else
			{
				// Free empty result set
				if (readings)
				{
					delete readings;
				}
				// Error or no data read: just wait
				// TODO: add increments from 1 to TASK_SLEEP_MAX_INCREMENTS
				this_thread::sleep_for(chrono::milliseconds(TASK_FETCH_SLEEP));
			}
                }
        }

#if VERBOSE_LOG
	Logger::getLogger()->info("SendingProcess loadData thread: Last ID '%s' read is %lu",
				  loadData->getDataSourceType().c_str(),
				  loadData->getLastFetchId());
#endif

	/**
	 * The loop is over: unlock the sendData thread
	 */
	unique_lock<mutex> lock(waitMutex);
	cond_var.notify_one();
}

/**
 * Thread to send data to historian service
 *
 * @param loadData    pointer to SendingProcess instance
 */
static void sendDataThread(SendingProcess *sendData)
{
	unsigned long totSent = 0;
	unsigned int  sendIdx = 0;

	bool slept;
	long sleep_time = TASK_SEND_SLEEP;
	int sleep_num_increments = 0;

        while (sendData->isRunning())
        {
		slept = false;

                if (sendIdx >= memoryBufferSize)
		{

			if (sendData->getUpdateDb())
			{
				// Update counters to Database
				sendData->updateDatabaseCounters();

				// Reset current sent readings
				sendData->resetSentReadings();	

				// DB update done
				sendData->setUpdateDb(false);
                        }

			// Reset send index
			sendIdx = 0;
		}

		/*
		 * Check whether m_buffer[sendIdx] is NULL or contains ReadinSet data.
		 * Access is protected by a mutex.
		 */
                readMutex.lock();
                ReadingSet *canSend = sendData->m_buffer.at(sendIdx);
                readMutex.unlock();

                if (canSend == NULL)
                {
#if VERBOSE_LOG
                        Logger::getLogger()->info("SendingProcess sendDataThread: " \
                                                  "('%s' stream id %d), sendIdx %u, buffer is empty, waiting ...",
						  sendData->getDataSourceType().c_str(),
                                                  sendData->getStreamId(),
                                                  sendIdx);
#endif

			if (sendData->getUpdateDb())
			{
                                // Update counters to Database
				sendData->updateDatabaseCounters();

				// Reset current sent readings
				sendData->resetSentReadings();	

				// DB update done
				sendData->setUpdateDb(false);
			}

			if (sendData->isRunning())
			{
				// Send thread is put on hold, only if the execution shoule proceed
				unique_lock<mutex> lock(waitMutex);
				cond_var.wait(lock);
			}
                }
                else
                {
			/**
			 * Send the buffer content ( const vector<Readings *>& )
			 * to historian server via m_plugin->send(data).
			 * Readings data by getAllReadings() will be
			 * transformed using historian protocol and then sent to destination.
			 */

			bool emptyReadings = sendData->m_buffer[sendIdx]->getCount() == 0;
			uint32_t sentReadings = 0;
			bool processUpdate = false;

			if (!emptyReadings)
			{
				// We have some readings to send
				const vector<Reading *> &readingData = sendData->m_buffer.at(sendIdx)->getAllReadings();
				sentReadings = sendData->m_plugin->send(readingData);
				// Check sent readings result
				if (sentReadings)
				{
					processUpdate = true;
					exitCode = 0;
				}
			}
			else
			{
				exitCode = 0;
				// We have an empty readings set: check last id
				if (sendData->m_last_read_id.at(sendIdx) > 0)
				{
					processUpdate = true;
				}
			}

			if (processUpdate)
			{
				exitCode = 0;

				/** Sending done */
				sendData->setUpdateDb(true);

				/**
				 * 1- emptying data in m_buffer[sendIdx].
				 * The buffer access is protected by a mutex.
				 */
				readMutex.lock();

				// Update last sent reading Id using the last id of the unfiltered readings buffer
				sendData->setLastSentId(sendData->m_last_read_id.at(sendIdx));

				// Free buffer
				delete sendData->m_buffer.at(sendIdx);
				sendData->m_buffer.at(sendIdx) = NULL;
				// Reset buffer last id
				sendData->m_last_read_id.at(sendIdx) = 0;

				/** 2- Update sent counter (memory only) */
				sendData->updateSentReadings(sentReadings);

				// numReadings sent so far
				totSent += sentReadings;

				readMutex.unlock();

				sendIdx++;

				// Unlock the loadData thread
				unique_lock<mutex> lock(waitMutex);
				cond_var.notify_one();
			}
			else
			{
				Logger::getLogger()->debug("SendingProcess sendDataThread: Error while sending " \
							   "('%s' stream id %d), sendIdx %u, N. (%d readings), " \
							   ", last reading id in buffer %ld",
							   sendData->getDataSourceType().c_str(),
							   sendData->getStreamId(),
							   sendIdx,
							   sendData->m_buffer[sendIdx]->getCount(),
							   sendData->m_last_read_id.at(sendIdx));

				if (sendData->getUpdateDb())
				{
					// Update counters to Database
					sendData->updateDatabaseCounters();

					// Reset current sent readings
					sendData->resetSentReadings();	

					// DB update done
					sendData->setUpdateDb(false);
				}

				// Error: just wait & continue
				this_thread::sleep_for(chrono::milliseconds(sleep_time));
				slept = true;
			}
                }

		// Handles the sleep time, it is doubled every time up to a limit
		if (slept)
		{
			sleep_num_increments += 1;
			sleep_time *= 2;
			if (sleep_num_increments >= TASK_SLEEP_MAX_INCREMENTS)
			{
				sleep_time = TASK_SEND_SLEEP;
				sleep_num_increments = 0;
			}
		}

        }
#if VERBOSE_LOG
	Logger::getLogger()->info("SendingProcess sendData thread: sent %lu total '%s'",
				  totSent,
				  sendData->getDataSourceType().c_str());
#endif

	if (sendData->getUpdateDb())
	{
                // Update counters to Database
		sendData->updateDatabaseCounters();

                // Reset current sent readings
		sendData->resetSentReadings();

                sendData->setUpdateDb(false);
        }

	/**
	 * The loop is over: unlock the loadData thread
	 */
	unique_lock<mutex> lock(waitMutex);
	cond_var.notify_one();
}

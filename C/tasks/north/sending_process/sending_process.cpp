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
#define TASK_SLEEP_MAX_INCREMENTS 4 // Currently not used

using namespace std;
using namespace std::chrono;

// Mutex for m_buffer access
mutex      readMutex;
// Mutex for thread idle time
mutex	waitMutex;
// Block the calling thread until notified to resume.
condition_variable cond_var;

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
        std::string tmp_str;

                // Instantiate SendingProcess class
		SendingProcess sendingProcess(argc, argv);
                
		// Launch the load thread
		sendingProcess.m_thread_load = new thread(loadDataThread, &sendingProcess);
		// Launch the send thread
		sendingProcess.m_thread_send = new thread(sendDataThread, &sendingProcess);

		// Run: max execution time or caught signals can stop it
		sendingProcess.run();

		// End processing
		sendingProcess.stop();
	}
	catch (const std::exception& e)
	{
		cerr << "Exception in " << argv[0] << " : " << e.what() << endl;
		// Return failure for class instance/configuration etc
		exit(1);
	}
	// Catch all exceptions
	catch (...)
	{
		std::exception_ptr p = std::current_exception();
		string name = (p ? p.__cxa_exception_type()->name() : "null");
		cerr << "Generic Exception in " << argv[0] << " : " << name << endl;
		exit(1);
	}

	// Return success
	exit(0);
}

/**
 * Thread to load data from the storage layer.
 *
 * @param loadData    pointer to SendingProcess instance
 */
static void loadDataThread(SendingProcess *loadData)
{
        unsigned int    readIdx = 0;

        while (loadData->isRunning())
        {
                if (readIdx >= DATA_BUFFER_ELMS)
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
			Logger::getLogger()->info("SendingProcess loadDataThread: "
						  "('%s' stream id %d), readIdx %u, buffer is NOT empty, waiting ...",
						  loadData->getDataSourceType().c_str(),
						  loadData->getStreamId(),
						  readIdx);

			// Load thread is put on hold
			unique_lock<mutex> lock(waitMutex);
			cond_var.wait(lock);
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
					unsigned long lastReadId = loadData->getLastSentId() + 1;
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
								to_string(loadData->getLastSentId()));
					vector<Returns *> columns;
					// Add colums and needed aliases
					columns.push_back(new Returns("id"));
					columns.push_back(new Returns("key", "asset_code"));
					columns.push_back(new Returns("key", "read_key"));
					columns.push_back(new Returns("ts"));
					columns.push_back(new Returns("history_ts", "user_ts"));
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
				// Update last fetched reading Id
				loadData->setLastSentId(readings->getLastId());

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
				 */
	                      	loadData->m_buffer.at(readIdx) = readings;

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

	Logger::getLogger()->info("SendingProcess loadData thread: Last ID '%s' read is %lu",
				  loadData->getDataSourceType().c_str(),
				  loadData->getLastSentId()); 

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

        while (sendData->isRunning())
        {
                if (sendIdx >= DATA_BUFFER_ELMS)
		{

			if (sendData->getUpdateDb())
			{
				// Update counters to Database
				sendData->updateDatabaseCounters();

				// numReadings sent so far
				totSent += sendData->getSentReadings();

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
                        Logger::getLogger()->info("SendingProcess sendDataThread: " \
                                                  "('%s' stream id %d), sendIdx %u, buffer is empty, waiting ...",
						  sendData->getDataSourceType().c_str(),
                                                  sendData->getStreamId(),
                                                  sendIdx);

			if (sendData->getUpdateDb())
			{
                                // Update counters to Database
				sendData->updateDatabaseCounters();

				// numReadings sent so far
				totSent += sendData->getSentReadings();

				// Reset current sent readings
				sendData->resetSentReadings();	

				// DB update done
				sendData->setUpdateDb(false);
			}

			// Send thread is put on hold
                        unique_lock<mutex> lock(waitMutex);
                        cond_var.wait(lock);
                }
                else
                {
			/**
			 * Send the buffer content ( const vector<Readings *>& )
			 * to historian server via m_plugin->send(data).
			 * Readings data by getAllReadings() will be
			 * transformed using historian protocol and then sent to destination.
			 */

			const vector<Reading *> &readingData = sendData->m_buffer.at(sendIdx)->getAllReadings();

			uint32_t sentReadings = sendData->m_plugin->send(readingData);

			if (sentReadings)
			{
				/** Sending done */
				sendData->setUpdateDb(true);

				/**
				 * 1- emptying data in m_buffer[sendIdx].
				 * The buffer access is protected by a mutex.
				 */
				readMutex.lock();

				delete sendData->m_buffer.at(sendIdx);
				sendData->m_buffer.at(sendIdx) = NULL;

				/** 2- Update sent counter (memory only) */
				sendData->updateSentReadings(sentReadings);

				readMutex.unlock();

				sendIdx++;

				// Unlock the loadData thread
				unique_lock<mutex> lock(waitMutex);
				cond_var.notify_one();
			}
			else
			{
				Logger::getLogger()->error("SendingProcess sendDataThread: Error while sending" \
							   "('%s' stream id %d), sendIdx %u. N. (%d readings)",
							   sendData->getDataSourceType().c_str(),
							   sendData->getStreamId(),
							   sendIdx,
							   sendData->m_buffer[sendIdx]->getCount());

				if (sendData->getUpdateDb())
				{
					// Update counters to Database
					sendData->updateDatabaseCounters();

					// numReadings sent so far
					totSent += sendData->getSentReadings();

					// Reset current sent readings
					sendData->resetSentReadings();	

					// DB update done
					sendData->setUpdateDb(false);
				}

				// Error: just wait & continue
				// TODO: add increments from 1 to TASK_SLEEP_MAX_INCREMENTS
				this_thread::sleep_for(chrono::milliseconds(TASK_SEND_SLEEP));
			}
                }
        }

	Logger::getLogger()->info("SendingProcess sendData thread: sent %lu total '%s'",
				  totSent,
				  sendData->getDataSourceType().c_str());

	if (sendData->getUpdateDb())
	{
                // Update counters to Database
		sendData->updateDatabaseCounters();

                // numReadings sent so far
		totSent += sendData->getSentReadings();

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


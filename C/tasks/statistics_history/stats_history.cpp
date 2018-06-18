/*
 * FogLAMP Statistics History
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <stats_history.h>
#include <csignal>


using namespace std;

volatile std::sig_atomic_t signalReceived = 0;

/**
 * Handle Signals
 */
static void signalHandler(int signal)
{
	signalReceived = signal;
}

/**
 * Constructor for Statistics history task
 */
StatsHistory::StatsHistory(int argc, char** argv) : FogLampProcess(argc, argv)
{
	Logger::getLogger()->info("StatsHistory starting");
}

/**
 * StatsHistory class methods
 */
StatsHistory::~StatsHistory()
{
}

/**
 * Statisitics History run method, called by the base class
 * to start the process and do the actual work.
 */
void StatsHistory::run() const
{
	// We handle these signals, add more if needed
	std::signal(SIGINT,  signalHandler);
	std::signal(SIGSTOP, signalHandler);
	std::signal(SIGTERM, signalHandler);

	// Get the set of distinct statistics keys
	Query query(new Returns("key"));
	query.distinct();
	ResultSet *keySet = getStorageClient()->queryTable("statistics", query);

	ResultSet::RowIterator rowIter = keySet->firstRow();

        do {
		string key = (*rowIter)->getColumn("key")->getString();
		try {
			processKey(key);
		} catch (exception e) {
			getLogger()->error("Failed to process statisitics key %s, %s", key, e.what());
		}
                rowIter = keySet->nextRow(rowIter);
	} while (keySet->hasNextRow(rowIter));

	delete keySet;
}

/**
 * Process a single statistics key
 *
 * @param key	The statistics key to process
 */
void StatsHistory::processKey(const string& key) const
{
Query	query(new Where("key", Equals, key));

	// Fetch the current and previous valaues for the key
	query.returns(new Returns("value"));
	query.returns(new Returns("previous_value"));
	ResultSet *values = getStorageClient()->queryTable("statistics", query);
	if (values->rowCount() != 1)
	{
		getLogger()->error("Internal error, failed to get statisitics for key %s", key.c_str());
		return;
	}
	int val = ((*values)[0])->getColumn("value")->getInteger();
	int prev = ((*values)[0])->getColumn("previous_value")->getInteger();
	delete values;
	
	// Insert the row into the configuration history
	InsertValues historyValues;
	historyValues.push_back(InsertValue("key", key.c_str()));
	historyValues.push_back(InsertValue("value", val - prev));
	historyValues.push_back(InsertValue("history_ts", "now()"));
	int n_rows;
	if ((n_rows = getStorageClient()->insertTable("statistics_history", historyValues)) != 1)
	{
		getLogger()->error("Failed to insert single row to statisitics history table for key %s", key.c_str());
	}

	// Update the previous value in the statistics row
	InsertValues updateValues;
	updateValues.push_back(InsertValue("previous_value", val));
	if (getStorageClient()->updateTable("statistics", updateValues, Where("key", Equals, key)) != 1)
	{
		getLogger()->error("Failed to update single row to statisitics table for key %s", key.c_str());
	}
}

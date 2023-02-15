/*
 * Fledge Statistics History
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
StatsHistory::StatsHistory(int argc, char** argv) : FledgeProcess(argc, argv)
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

	if (m_dryRun)
		return;

	Logger::getLogger()->error("StatsHistory::run() started");
	// Get the set of distinct statistics keys
	Query query(new Returns("key"));
	query.distinct();
	ResultSet *keySet = getStorageClient()->queryTable("statistics", query);

	ResultSet::RowIterator rowIter = keySet->firstRow();
	InsertValues historyValues;
	vector<pair<InsertValue *, Where *>> updateValues;

        do {
		string key = (*rowIter)->getColumn("key")->getString();
		Logger::getLogger()->error("StatsHistory::calling processKey for key:%s", key.c_str());
		try {
			processKey(key, historyValues, updateValues);
		} catch (exception e) {
			getLogger()->error("Failed to process statisitics key %s, %s", key, e.what());
		}
                rowIter = keySet->nextRow(rowIter);
	} while (keySet->hasNextRow(rowIter));

	Logger::getLogger()->error("+++++++++++++++++++++++calling insertTable");

	Logger::getLogger()->error("+++++++++++++++++++++++processKey::historyValues.size() = %d", historyValues.size());
	Logger::getLogger()->error("+++++++++++++++++++++++processKey::updateValues.size() = %d", updateValues.size());
	int n_rows;
        if ((n_rows = getStorageClient()->insertTable("statistics_history", historyValues)) < 1)
        {
                getLogger()->error("Failed to insert rows to statisitics history table ");
        }

	Logger::getLogger()->error("+++++++++++++++++++++++++++++calling updateTable");

	if (getStorageClient()->updateTable("statistics", updateValues) < 1)
        {
                getLogger()->error("Failed to update rows to statisitics table");
        }

	for (auto it = updateValues.begin(); it != updateValues.end() ; ++it)
	{
		InsertValue *updateValue = it->first;
		if (updateValue)
		{
			delete updateValue;
			updateValue=nullptr;
		}
        	Where *wKey = it->second;
		if(wKey)
		{
			delete wKey;
			wKey = nullptr;
		}
	}

	delete keySet;
}

/**
 * Process a single statistics key
 *
 * @param key	The statistics key to process
 */
void StatsHistory::processKey(const string& key, InsertValues& historyValues, std::vector<std::pair<InsertValue*, Where *> > &updateValues) const
{
	Query	query(new Where("key", Equals, key));

	Logger::getLogger()->error("processKey start");
	// Fetch the current and previous valaues for the key
	query.returns(new Returns("value"));
	query.returns(new Returns("previous_value"));
	ResultSet *values = getStorageClient()->queryTable("statistics", query);

	Logger::getLogger()->error("processKey : after query statistics table");
	if (values->rowCount() != 1)
	{
		getLogger()->error("Internal error, failed to get statisitics for key %s", key.c_str());
		return;
	}
	int val = ((*values)[0])->getColumn("value")->getInteger();
	int prev = ((*values)[0])->getColumn("previous_value")->getInteger();
	delete values;
	
	// Insert the row into the configuration history
	historyValues.push_back(InsertValue("key", key.c_str()));
	historyValues.push_back(InsertValue("value", val - prev));
	historyValues.push_back(InsertValue("history_ts", "now()"));

	// Update the previous value in the statistics row

	InsertValue *updateValue = new InsertValue("previous_value", val);
	Where *wKey = new Where("key", Equals, key);
	updateValues.emplace_back(updateValue, wKey);

	Logger::getLogger()->error("processKey end");
}

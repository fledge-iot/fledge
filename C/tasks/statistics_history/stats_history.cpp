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
#define MAXSIZE 200

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

	// Get the set of distinct statistics keys
	Query query(new Returns("key"));
	query.distinct();
	ResultSet *keySet = getStorageClient()->queryTable("statistics", query);

	ResultSet::RowIterator rowIter = keySet->firstRow();
	std::vector<InsertValues> historyValues;
	vector<pair<InsertValue *, Where *>> updateValues;

        do {
		string key = (*rowIter)->getColumn("key")->getString();

		try {
			processKey(key, historyValues, updateValues);
		} catch (exception e) {
			getLogger()->error("Failed to process statisitics key %s, %s", key, e.what());
		}
                rowIter = keySet->nextRow(rowIter);
	} while (keySet->hasNextRow(rowIter));

	int n_rows;

        if ((n_rows = getStorageClient()->insertTable("statistics_history", historyValues)) < 1)
        {
                getLogger()->error("Failed to insert rows to statisitics history table ");
        }

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
 * Process statistics keys
 *
 * @param key	         The statistics key to process
 * @param historyValues  Values to be inserted in statistics_history
 * @param updateValues   Values to be updated in statistics
 * @return void
 */
void StatsHistory::processKey(const std::string& key, std::vector<InsertValues> &historyValues, std::vector<std::pair<InsertValue*, Where *> > &updateValues) const
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

	InsertValues iValue;

	time_t t;
	struct tm *tmp ;
	char localTime[MAXSIZE];
	time(&t);	
	tmp = localtime(&t);
	strftime(localTime, sizeof(localTime), "%Y-%m-%d %H:%M:%s", tmp);

	// Insert the row into the configuration history
	iValue.push_back(InsertValue("key", key.c_str()));
	iValue.push_back(InsertValue("value", val - prev));
	iValue.push_back(InsertValue("history_ts", localTime));

	historyValues.push_back(iValue);

	// Update the previous value in the statistics row

	InsertValue *updateValue = new InsertValue("previous_value", val);
	Where *wKey = new Where("key", Equals, key);
	updateValues.emplace_back(updateValue, wKey);
}

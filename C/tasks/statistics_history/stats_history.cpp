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
#include <time.h>
#include <sys/time.h>

#define DATETIME_MAX_LEN 52
#define MICROSECONDS_FORMAT_LEN	10
#define DATETIME_FORMAT_DEFAULT	"%Y-%m-%d %H:%M:%S"

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
        query.returns(new Returns("value"));
        query.returns(new Returns("previous_value"));
        ResultSet *keySet = getStorageClient()->queryTable("statistics", query);

	ResultSet::RowIterator rowIter = keySet->firstRow();
	std::vector<InsertValues> historyValues;
	vector<pair<InsertValue *, Where *>> updateValues;

	std::string dateTimeStr = getTime();

        while (keySet->hasNextRow(rowIter) || keySet->isLastRow(rowIter) )
	{
		string key = (*rowIter)->getColumn("key")->getString();
		int val = (*rowIter)->getColumn("value")->getInteger();
        	int prev = (*rowIter)->getColumn("previous_value")->getInteger();

		try {
			processKey(key, historyValues, updateValues, dateTimeStr, val, prev);
		} catch (exception e) {
			getLogger()->error("Failed to process statisitics key %s, %s", key, e.what());
		}
		if (!keySet->isLastRow(rowIter))
                	rowIter = keySet->nextRow(rowIter);
		else
			break;
	}

	int n_rows;
        if ((n_rows = getStorageClient()->insertTable("statistics_history", historyValues)) < 1)
        {
                getLogger()->error("Failed to insert rows to statistics history table ");
        }

	if (getStorageClient()->updateTable("statistics", updateValues) < 1)
        {
                getLogger()->error("Failed to update rows to statistics table");
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
 * @param dateTimeStr    Local time with microseconds precision 
 * @param val		 int 
 * @param prev		 int 
 * @return void
 */
void StatsHistory::processKey(const std::string& key, std::vector<InsertValues> &historyValues, std::vector<std::pair<InsertValue*, Where *> > &updateValues, std::string dateTimeStr, int val, int prev) const
{
	InsertValues iValue;

	// Insert the row into the statistics history
	// create an object of InsertValues and push in historyValues vector
	// for batch insertion
	iValue.push_back(InsertValue("key", key.c_str()));
	iValue.push_back(InsertValue("value", val - prev));
	iValue.push_back(InsertValue("history_ts", dateTimeStr));

	historyValues.push_back(iValue);

	// Update the previous value in the statistics row
	// create an object of InsertValue and push in updateValues vector
	// for batch updation
	InsertValue *updateValue = new InsertValue("previous_value", val);
	Where *wKey = new Where("key", Equals, key);
	updateValues.emplace_back(updateValue, wKey);
}

/**
 * getTime() function returns the localTime with microseconds precision  
 *
 * @param  void 
 * @return std::string localTime
 */

std::string StatsHistory::getTime(void) const
{
	struct timeval tv ;
	struct tm* timeinfo;
	gettimeofday(&tv, NULL);
	timeinfo = gmtime(&tv.tv_sec);
	char date_time[DATETIME_MAX_LEN];
	// Create datetime with seconds
	strftime(date_time,
		    sizeof(date_time),
		    DATETIME_FORMAT_DEFAULT,
		    timeinfo);

	std::string dateTimeLocal = date_time;
	char micro_s[MICROSECONDS_FORMAT_LEN];
	// Add microseconds
	snprintf(micro_s,
		    sizeof(micro_s),
		    ".%06lu",
		    tv.tv_usec);

	dateTimeLocal.append(micro_s);
	return dateTimeLocal;
}


#ifndef _STATISTICS_HISTORY_H
#define _STATISTICS_HISTORY_H

/*
 * Fledge Statistics History
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <process.h>


/**
 * StatisticsHisotry class
 */
class StatsHistory : public FledgeProcess
{
	public:
		// Constructor:
		StatsHistory(int argc, char** argv);
		// Destructor
		~StatsHistory();

		void			run() const;

	private:
		void processKey(const string& key, InsertValues& historyValues, vector<pair<InsertValues *, Where *>> &updateValues) const;

};

#endif

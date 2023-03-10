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
#include <vector>
#include <string>
#include <utility>


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
		void processKey(const std::string& key, std::vector<InsertValues> &historyValues, 
			std::vector<std::pair<InsertValue *, Where *> > &updateValues, std::string dateTimeStr, int val , int prev) const;
		std::string getTime(void) const;


};

#endif

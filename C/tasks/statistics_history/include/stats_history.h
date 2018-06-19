#ifndef _STATISTICS_HISTORY_H
#define _STATISTICS_HISTORY_H

/*
 * FogLAMP Statistics History
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
class StatsHistory : public FogLampProcess
{
	public:
		// Constructor:
		StatsHistory(int argc, char** argv);
		// Destructor
		~StatsHistory();

		void			run() const;

	private:
		void	processKey(const std::string& key) const;
};

#endif

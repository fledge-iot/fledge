#ifndef _STORAGE_STATS_H
#define _STORAGE_STATS_H
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <string>

class StorageStats {
	public:
		StorageStats();
		void		asJSON(std::string &);
		unsigned int commonInsert;
		unsigned int commonSimpleQuery;
		unsigned int commonQuery;
		unsigned int commonUpdate;
		unsigned int commonDelete;
		unsigned int readingAppend;
		unsigned int readingFetch;
		unsigned int readingQuery;
		unsigned int readingPurge;
};
#endif

#ifndef _STORAGE_STATS_H
#define _STORAGE_STATS_H

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

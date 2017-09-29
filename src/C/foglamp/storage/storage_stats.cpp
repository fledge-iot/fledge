/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <storage_stats.h>
#include <string>
#include <sstream>

using namespace std;

/**
 * Construct the statistics class for the storage service.
 */
StorageStats::StorageStats() : commonInsert(0), commonSimpleQuery(0),
				commonQuery(0), commonUpdate(0), commonDelete(0),
				readingAppend(0), readingFetch(0),
				readingQuery(0), readingPurge(0)
{
}

/**
 * Serialise the statistics as JSON
 */
void StorageStats::asJSON(string& json)
{
ostringstream convert;   // stream used for the conversion

	convert << "{ \"commonInsert\" : " << commonInsert << ",";
	convert << " \"commonSimpleQuery\" : " << commonSimpleQuery << ",";
	convert << " \"commonQuery\" : " << commonQuery << ",";
	convert << " \"commonUpdate\" : " << commonUpdate << ",";
	convert << " \"commonDelete\" : " << commonDelete << ",";
	convert << " \"readingAppend\" : " << readingAppend << ",";
	convert << " \"readingFetch\" : " << readingFetch << ",";
	convert << " \"readingQuery\" : " << readingQuery << ",";
	convert << " \"readingPurge\" : " << readingPurge << " }";

	json = convert.str();
}

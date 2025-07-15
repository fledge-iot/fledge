/*
 * unit tests FOGL-9849 : Add merge function to ReadingSet
 *
 * Copyright (c) 2025 Dianomic Systems, Inc.
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <gtest/gtest.h>
#include <reading.h>
#include <reading_set.h>
#include <datapoint.h>
#include <cassert>
#include <iostream>


// Helper to create a reading with a specific timestamp
Reading* createReading(const std::string& asset, const std::string& dpName, long value, struct timeval ts)
{
	std::vector<Datapoint *> dps;
	DatapointValue dp1(value);
	dps.push_back(new Datapoint(dpName, dp1));
	Reading* r = new Reading(asset, dps);
	r->setUserTimestamp(ts);
	return r;
}

// Reading to be merged with the ReadingSet which has same timestamp
TEST(ReadingSetMerge, ReadingsWithSameTimestamp)
{
	struct timeval ts1 = { 100, 0 };  // Earliest
	struct timeval ts2 = { 200, 0 };
	struct timeval ts3 = { 300, 0 };
	struct timeval ts4 = { 200, 0 };  // Duplicate timestamp with ts2

	// Step 1: Initial ReadingSet with ts1 and ts3
	Reading* r1 = createReading("asset1", "dp1", 10, ts1);
	Reading* r3 = createReading("asset3", "dp3", 30, ts3); 

	std::vector<Reading*> initialReadings = { r1, r3 };
	ReadingSet set(&initialReadings);  // Initial state

	assert(set.getCount() == 2);

	// Step 2: Vector to merge
	std::vector<Reading*> toMerge;
	Reading* r2 = createReading("asset2", "dp2", 20, ts2); 
	Reading* r4 = createReading("asset4", "dp4", 40, ts4);

	toMerge.push_back(r2);
	toMerge.push_back(r4);

	set.merge(&toMerge);  // In-place merge

	// Step 3: Validate ordering and content
	assert(set.getCount() == 4);
	assert(toMerge.empty());

	std::vector<Reading*> merged = set.getAllReadings();

	// Order should be: r1(ts1), r2(ts2), r4(ts4), r3(ts3)
	assert(merged[0]->getAssetName() == "asset1");
	assert(merged[1]->getAssetName() == "asset2");
	assert(merged[2]->getAssetName() == "asset4");
	assert(merged[3]->getAssetName() == "asset3");

	// Step 4: Validate timestamps are non-decreasing
	for (size_t i = 1; i < merged.size(); ++i)
	{
		struct timeval prev; merged[i - 1]->getUserTimestamp(&prev);
		struct timeval curr; merged[i]->getUserTimestamp(&curr);
		assert(timercmp(&prev, &curr, <) || timercmp(&prev, &curr, ==));
	}
}

// Reading to be merged with the ReadingSet which has duplicate timestamp
TEST(ReadingSetMerge, ReadingsWithDuplicateTimestamp)
{
	struct timeval ts1 = { 100, 0 };  // Earliest
	struct timeval ts2 = { 200, 0 };
	struct timeval ts3 = { 300, 0 };
	struct timeval ts4 = { 200, 0 };  // Duplicate timestamp with ts2

	// Step 1: Initial ReadingSet with ts1 and ts4
	Reading* r1 = createReading("asset1", "dp1", 10, ts1);
	Reading* r4 = createReading("asset4", "dp4", 40, ts4);
	

	std::vector<Reading*> initialReadings = { r1, r4 };
	ReadingSet set(&initialReadings); // Initial state

	assert(set.getCount() == 2);

	// Step 2: Vector to merge
	std::vector<Reading*> toMerge;
	Reading* r2 = createReading("asset2", "dp2", 20, ts2);  
	Reading* r3 = createReading("asset3", "dp3", 30, ts3);  
	

	toMerge.push_back(r2);
	toMerge.push_back(r3);

	set.merge(&toMerge);  // In-place merge

	// Step 3: Validate ordering and content
	assert(set.getCount() == 4);
	assert(toMerge.empty());

	std::vector<Reading*> merged = set.getAllReadings();

	// Order should be: r1(ts1), r4(ts4), r2(ts2), r3(ts3)
	assert(merged[0]->getAssetName() == "asset1");
	// Reading in the existing ReadingSet must come before the new reading with the same timestamp
	assert(merged[1]->getAssetName() == "asset4");
	assert(merged[2]->getAssetName() == "asset2");
	assert(merged[3]->getAssetName() == "asset3");

	// Step 4: Validate timestamps are non-decreasing
	for (size_t i = 1; i < merged.size(); ++i)
	{
		struct timeval prev; merged[i - 1]->getUserTimestamp(&prev);
		struct timeval curr; merged[i]->getUserTimestamp(&curr);
		assert(timercmp(&prev, &curr, <) || timercmp(&prev, &curr, ==));
	}
}
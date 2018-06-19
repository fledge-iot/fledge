#include <gtest/gtest.h>
#include <purge_result.h>
#include <string.h>
#include <string>
#include <rapidjson/document.h>

using namespace std;
using namespace rapidjson;

TEST(PurgeResult, Values)
{
const char *input = "{ \"removed\" : 1234, \"unsentPurged\" : 0, "
		"\"unsentRetained\" : 100, \"readings\" : 1000 }";

	PurgeResult purgeResult(input);
	ASSERT_EQ(1234, purgeResult.getRemoved());
	ASSERT_EQ(0, purgeResult.getUnsentPurged());
	ASSERT_EQ(100, purgeResult.getUnsentRetained());
	ASSERT_EQ(1000, purgeResult.getRemaining());
}

TEST(PurgeResult, UnsentPurged)
{
const char *input = "{ \"removed\" : 1234, \"unsentPurged\" : 100, "
		"\"unsentRetained\" : 0, \"readings\" : 1000 }";

	PurgeResult purgeResult(input);
	ASSERT_EQ(1234, purgeResult.getRemoved());
	ASSERT_EQ(100, purgeResult.getUnsentPurged());
	ASSERT_EQ(0, purgeResult.getUnsentRetained());
	ASSERT_EQ(1000, purgeResult.getRemaining());
}

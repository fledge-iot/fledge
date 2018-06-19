#include <gtest/gtest.h>
#include <reading_set.h>
#include <string.h>
#include <string>
#include <rapidjson/document.h>

using namespace std;
using namespace rapidjson;

const char *input = "{ \"count\" : 2, \"rows\" : [ "
	    "{ \"id\": 1, \"asset_code\": \"luxometer\", "
            "\"read_key\": \"5b3be500-ff95-41ae-b5a4-cc99d08bef4a\", "
            "\"reading\": { \"lux\": 76204.524 }, "
            "\"user_ts\": \"2017-09-21 15:00:08.532958\", "
            "\"ts\": \"2017-09-22 14:47:18.872708\" }, "
	    "{ \"id\": 2, \"asset_code\": \"luxometer\", "
            "\"read_key\": \"5b3be50c-ff95-41ae-b5a4-cc99d08bef4a\", "
            "\"reading\": { \"lux\": 76834.361 }, "
            "\"user_ts\": \"2017-09-21 15:00:09.32958\", "
            "\"ts\": \"2017-09-22 14:48:18.72708\" }"
	    "] }";

TEST(ReadingSet, Count)
{
	ReadingSet readingSet(input);
	ASSERT_EQ(2, readingSet.getCount());
}

TEST(ReadingSet, Index)
{
	ReadingSet readingSet(input);
	const Reading *reading = readingSet[0];
	string json = reading->toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"luxmeter\"")), 0);
	ASSERT_NE(json.find(string("\"reading\" : { \"lux\" : \"76204.524\" }")), 0);
	ASSERT_NE(json.find(string("\"readkey\" : ")), 0);
	ASSERT_NE(json.find(string("\"user_ts\" : \"2017-09-22 14:47:18.872708\"")), 0);
}

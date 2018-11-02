
#include <gtest/gtest.h>
#include <reading_set.h>
#include <string.h>
#include <string>
#include <rapidjson/document.h>

using namespace std;
using namespace rapidjson;

const char *inputData = "{ \"id\": 17651, \"asset_code\": \"luxometer\", "
            "\"read_key\": \"5b3be500-ff95-41ae-b5a4-cc99d08bef4a\", "
            "\"reading\": { \"lux\": 76204.524 }, "
            "\"user_ts\": \"2017-09-21 15:00:08.532958\", "
            "\"ts\": \"2017-09-22 14:47:18.872708\" }";

TEST(JSONReadingTest, ParseReading)
{
	Document doc;
	doc.Parse(inputData);
	JSONReading reading(doc);
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"luxmeter\"")), 0);
	ASSERT_NE(json.find(string("\"reading\" : { \"lux\" : \"76204.524\" }")), 0);
	ASSERT_NE(json.find(string("\"readkey\" : ")), 0);
	ASSERT_NE(json.find(string("\"user_ts\" : \"2017-09-22 14:47:18.872708\"")), 0);
}

TEST(JSONReadingTest, CopyReading)
{
	Document doc;
	doc.Parse(inputData);
	JSONReading reading(doc);
	// Copy Reading	into a new variable
	Reading copyReading(reading);

	// Get JSON string of both reading objects
	string json = reading.toJSON();
	string copyJson = copyReading.toJSON();

	ASSERT_NE(json.find(string("\"asset_code\" : \"luxometer\"")), std::string::npos);
	ASSERT_NE(json.find(string("\"reading\" : { \"lux\" : 76204.524 }")), std::string::npos);
	ASSERT_NE(json.find(string("\"read_key\" : ")), std::string::npos);
	ASSERT_NE(json.find(string("\"user_ts\" : ")), std::string::npos);

	// Check JSON object as string
	ASSERT_EQ(json, copyJson);

	// Check reading id is the same: copy is ok
	ASSERT_EQ(reading.getId(), copyReading.getId());
}

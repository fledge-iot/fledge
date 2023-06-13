
#include <gtest/gtest.h>
#include <reading_set.h>
#include <string.h>
#include <string>
#include <rapidjson/document.h>

using namespace std;
using namespace rapidjson;

const char *inputData = "{ \"id\": 17651, \"asset_code\": \"luxometer\", "
            "\"reading\": { \"lux\": 76204.524 }, "
            "\"user_ts\": \"2017-09-21 15:00:08.532958\", "
            "\"ts\": \"2017-09-22 14:47:18.872708\" }";

const char *inputData2 = "{ \"id\": 17651, \"asset_code\": \"luxometer\", "
            "\"reading\": { \"lux\": 76204.524, \"longint\", 12345678901234567890 }, "
            "\"user_ts\": \"2017-09-21 15:00:08.532958\", "
 	    "\"ts\": \"2017-09-22 14:47:18.872708\" }";

const char *inputData3 = "{ \"id\": 17651, \"asset_code\": \"luxometer\", "
            "\"reading\": { \"lux\": 76204.524, \"longint\", 65535 }, "
            "\"user_ts\": \"2017-09-21 15:00:08.532958\", "
 	    "\"ts\": \"2017-09-22 14:47:18.872708\" }";

const char *inputData4 = "{ \"id\": 17651, \"asset_code\": \"luxometer\", "
            "\"reading\": { \"lux\": 76204.524, \"longint\", 4294836225 }, "
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

	ASSERT_NE(json.find(string("\"asset_code\":\"luxometer\"")), std::string::npos);
	ASSERT_NE(json.find(string("\"reading\":{\"lux\":76204.524}")), std::string::npos);
	ASSERT_NE(json.find(string("\"user_ts\":")), std::string::npos);

	// Check JSON object as string
	ASSERT_EQ(json, copyJson);

	// Check reading id is the same: copy is ok
	ASSERT_EQ(reading.getId(), copyReading.getId());
}

TEST(JSONReadingTest, ParseLongIntReading)
{
	Document doc;
	doc.Parse(inputData2);
	JSONReading reading(doc);
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"luxmeter\"")), 0);
	ASSERT_NE(json.find(string("\"reading\" : { \"lux\" : \"76204.524\", \"longint\" : \"12345678901234567890\" }")), 0);
	ASSERT_NE(json.find(string("\"user_ts\" : \"2017-09-22 14:47:18.872708\"")), 0);
}

TEST(JSONReadingTest, Parse65535Reading)
{
	Document doc;
	doc.Parse(inputData3);
	JSONReading reading(doc);
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"luxmeter\"")), 0);
	ASSERT_NE(json.find(string("\"reading\" : { \"lux\" : \"76204.524\", \"longint\" : \"65535\" }")), 0);
	ASSERT_NE(json.find(string("\"user_ts\" : \"2017-09-22 14:47:18.872708\"")), 0);
}

TEST(JSONReadingTest, Parse4294836225Reading)
{
	Document doc;
	doc.Parse(inputData4);
	JSONReading reading(doc);
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"luxmeter\"")), 0);
	ASSERT_NE(json.find(string("\"reading\" : { \"lux\" : \"76204.524\", \"longint\" : \"4294836225\" }")), 0);
	ASSERT_NE(json.find(string("\"user_ts\" : \"2017-09-22 14:47:18.872708\"")), 0);
}

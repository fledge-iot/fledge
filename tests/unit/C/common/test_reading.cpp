#include <gtest/gtest.h>
#include <reading.h>
#include <string.h>
#include <string>

using namespace std;

TEST(ReadingTest, IntValue)
{
	DatapointValue value(10);
	Reading reading(string("test1"), new Datapoint("x", value));
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"test1\"")), 0);
	ASSERT_NE(json.find(string("\"reading\" : { \"x\" : \"10\" }")), 0);
	ASSERT_NE(json.find(string("\"readkey\" : ")), 0);
	ASSERT_NE(json.find(string("\"ser_ts\" : ")), 0);
}

TEST(ReadingTest, FloatValue)
{
	DatapointValue value(3.1415);
	Reading reading(string("test1"), new Datapoint("pi", value));
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"test1\"")), 0);
	ASSERT_NE(json.find(string("\"reading\" : { \"pi\" : \"3.1415\" }")), 0);
	ASSERT_NE(json.find(string("\"readkey\" : ")), 0);
	ASSERT_NE(json.find(string("\"ser_ts\" : ")), 0);
}

#include <gtest/gtest.h>
#include <reading.h>
#include <string.h>
#include <string>
#include <vector>

using namespace std;

TEST(ReadingTest, IntValue)
{
	DatapointValue value((long) 10);
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

TEST(ReadingTest, AString)
{
	DatapointValue value("just a string");
	Reading reading(string("test3"), new Datapoint("str", value));
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"test3\"")), std::string::npos);
	ASSERT_NE(json.find(string("\"reading\" : { \"str\" : \"just a string\" }")), std::string::npos);
	ASSERT_NE(json.find(string("\"read_key\" : ")), std::string::npos);
	ASSERT_NE(json.find(string("\"user_ts\" : ")), std::string::npos);
}

TEST(ReadingTest, FloatArray)
{
	std::vector<double> v {3.1415, -128, 0, -0.0021, 0.2345};
	DatapointValue value(v);
	Reading reading(string("test55"), new Datapoint("a", value));
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"test55\"")), std::string::npos);
	ASSERT_NE(json.find(string("\"reading\" : { \"a\" : [3.1415, -128, 0, -0.0021, 0.2345] }")), std::string::npos);
	ASSERT_NE(json.find(string("\"read_key\" : \"")), std::string::npos);
	ASSERT_NE(json.find(string("\"user_ts\" : ")), std::string::npos);
}

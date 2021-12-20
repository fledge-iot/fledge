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
	ASSERT_NE(json.find(string("\"ser_ts\" : ")), 0);
}

TEST(ReadingTest, FloatValue)
{
	DatapointValue value(3.1415);
	Reading reading(string("test1"), new Datapoint("pi", value));
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"test1\"")), 0);
	ASSERT_NE(json.find(string("\"reading\" : { \"pi\" : \"3.1415\" }")), 0);
	ASSERT_NE(json.find(string("\"ser_ts\" : ")), 0);
}

TEST(ReadingTest, AString)
{
	DatapointValue value("just a string");
	Reading reading(string("test3"), new Datapoint("str", value));
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\":\"test3\"")), std::string::npos);
	ASSERT_NE(json.find(string("\"reading\":{\"str\":\"just a string\"}")), std::string::npos);
	ASSERT_NE(json.find(string("\"user_ts\":")), std::string::npos);
}

TEST(ReadingTest, FloatArray)
{
	std::vector<double> v {3.1415, -128, 0, -0.0021, 0.2345};
	DatapointValue value(v);
	Reading reading(string("test55"), new Datapoint("a", value));
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\":\"test55\"")), std::string::npos);
	ASSERT_NE(json.find(string("\"reading\":{\"a\":[3.1415, -128, 0, -0.0021, 0.2345]}")), std::string::npos);
	ASSERT_NE(json.find(string("\"user_ts\":")), std::string::npos);
}

TEST(ReadingTest, GMT)
{
	DatapointValue value((long) 10);
	Reading reading(string("test1"), new Datapoint("x", value));
	reading.setUserTimestamp("2019-01-10 10:01:03.123456+0:00");
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"user_ts\" : \"2019-01-10 10:01:03.123456+0:00\"")), 0);
}

TEST(ReadingTest, CET)
{
	DatapointValue value((long) 10);
	Reading reading(string("test1"), new Datapoint("x", value));
	reading.setUserTimestamp("2019-01-10 10:01:03.123456-1:00");
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"user_ts\" : \"2019-01-10 11:01:03.123456+0:00\"")), 0);
}

TEST(ReadingTest, PST)
{
	DatapointValue value((long) 10);
	Reading reading(string("test1"), new Datapoint("x", value));
	reading.setUserTimestamp("2019-01-10 10:01:03.123456+8:00");
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"user_ts\" : \"2019-01-10 18:01:03.123456+0:00\"")), 0);
}

TEST(ReadingTest, IST)
{
	DatapointValue value((long) 10);
	Reading reading(string("test1"), new Datapoint("x", value));
	reading.setUserTimestamp("2019-01-10 10:01:03.123456-5:30");
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"user_ts\" : \"2019-01-10 15:31:03.123456+0:00\"")), 0);
}

TEST(ReadingTest, rmDatapoint)
{
	DatapointValue value((long) 10);
	Reading reading(string("test1"), new Datapoint("x", value));
	DatapointValue val2((long) 20);
	reading.addDatapoint(new Datapoint("y", val2));
	ASSERT_EQ(reading.getDatapointCount(), 2);
	Datapoint *removed = reading.removeDatapoint("x");
	ASSERT_EQ(reading.getDatapointCount(), 1);
	ASSERT_EQ(removed->getName().compare("x"), 0);
	delete removed;
	removed = reading.removeDatapoint("x");
	ASSERT_EQ(removed,  (Datapoint *)0);
}

TEST(ReadingTest, DictDatapoint)
{
	DatapointValue dpv1(1.0);
	DatapointValue dpv2(1.1);
	vector<Datapoint *> *values = new vector<Datapoint *>;
	values->push_back(new Datapoint("first", dpv1));
	values->push_back(new Datapoint("second", dpv2));
	// Create a dict
	DatapointValue dpv(values, true);

	Reading reading(string("test55"), new Datapoint("a", dpv));
	string json = reading.toJSON();

	// Expected output: {"a":{"first":1.0, "second":1.1}}
	ASSERT_NE(json.find(string("\"reading\":{\"a\":{\"first\":1.0, \"second\":1.1}}")), std::string::npos);
}

TEST(ReadingTest, ArrayOfDicts)
{
	DatapointValue dpv1(1.0);
	DatapointValue dpv2(1.1);

	vector<Datapoint *> *val1 = new vector<Datapoint *>;
	val1->push_back(new Datapoint("first", dpv1));
	// Create an array of dicts, one entry
	DatapointValue dpv_1(val1, true); // put this into a dict of its own

	vector<Datapoint *> *val2 = new vector<Datapoint *>;
	val2->push_back(new Datapoint("second", dpv2));
	// Create an array of dicts, one entry
	DatapointValue dpv_2(val2, true); // put this into a dict of its own

	std::vector<Datapoint*>* dpVec = new std::vector<Datapoint *>();

	// Create a datapoints with unamed elements
	dpVec->emplace_back(new Datapoint(std::string("unnamed_list_elem#1"), dpv_1));
	dpVec->emplace_back(new Datapoint(std::string("unnamed_list_elem#2"), dpv_2));
	DatapointValue dpv(dpVec, false); // put dicts into list

	// Expected output: {"a":[{"first":1.0}, {"second":1.1}]}
	Reading reading(string("test55"), new Datapoint("a", dpv));
	string json = reading.toJSON();

	ASSERT_NE(json.find(string("\"reading\":{\"a\":[{\"first\":1.0}, {\"second\":1.1}]}")), std::string::npos);
}

TEST(ReadingTest, FMTDEFAULT)
{
	DatapointValue value((long) 10);
	Reading reading(string("test1"), new Datapoint("x", value));
	reading.setUserTimestamp("2019-01-10 10:01:03.123456+0:00");
	string datetime = reading.getAssetDateUserTime(Reading::FMT_DEFAULT);
	ASSERT_EQ(datetime.compare("2019-01-10 10:01:03.123456"), 0);
}

TEST(ReadingTest, FMTSTANDARD)
{
	DatapointValue value((long) 10);
	Reading reading(string("test1"), new Datapoint("x", value));
	reading.setUserTimestamp("2019-01-10 10:01:03.123456+0:00");
	string datetime = reading.getAssetDateUserTime(Reading::FMT_STANDARD);
	ASSERT_EQ(datetime.compare("2019-01-10T10:01:03.123456"), 0);
}

TEST(ReadingTest, ISO8601MS)
{
	DatapointValue value((long) 10);
	Reading reading(string("test1"), new Datapoint("x", value));
	reading.setUserTimestamp("2019-01-10 10:01:03.123456+0:00");
	string datetime = reading.getAssetDateUserTime(Reading::FMT_ISO8601MS);
	ASSERT_EQ(datetime.compare("2019-01-10 10:01:03.123456 +0000"), 0);
}

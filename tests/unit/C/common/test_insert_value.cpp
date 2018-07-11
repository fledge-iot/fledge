#include <gtest/gtest.h>
#include <insert.h>
#include <string.h>
#include <string>
#include <rapidjson/document.h>

using namespace std;
using namespace rapidjson;

TEST(InsertValueTest, IntColumn)
{
string expected("\"c1\" : 10");

	InsertValue value("c1", 10);
	ASSERT_EQ(expected.compare(value.toJSON()), 0);
}

TEST(InsertValueTest, LongColumn)
{
string expected("\"c1\" : 12345678");

	InsertValue value("c1", 12345678L);
	ASSERT_EQ(expected.compare(value.toJSON()), 0);
}

TEST(InsertValueTest, NumberColumn)
{
string expected("\"c1\" : 123.4");

	InsertValue value("c1", 123.4);
	ASSERT_EQ(expected.compare(value.toJSON()), 0);
}

TEST(InsertValueTest, StringColumn)
{
string expected("\"c1\" : \"hello\"");

	InsertValue value("c1", "hello");
	ASSERT_EQ(expected.compare(value.toJSON()), 0);
}

TEST(InsertValuesTest, IntColumns)
{
string expected("{ \"c1\" : 1, \"c2\" : 2 }");

	InsertValues values;
	values.push_back(InsertValue("c1", 1));
	values.push_back(InsertValue("c2", 2));
	ASSERT_EQ(expected.compare(values.toJSON()), 0);
}

TEST(InsertValueTest, JSONColumn)
{
string expected("\"c1\" : {\"hello\":\"world\"}");

	Document doc;
	doc.Parse("{\"hello\":\"world\"}");
	InsertValue value("c1", doc);
	ASSERT_EQ(expected.compare(value.toJSON()), 0);
}

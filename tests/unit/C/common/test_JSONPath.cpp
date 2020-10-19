#include <gtest/gtest.h>
#include <JSONPath.h>
#include <rapidjson/document.h>
#include <string.h>
#include <string>

using namespace std;
using namespace rapidjson;

const char *testdoc = "{ \"a\" : { \"b\" : \"x\" }, " \
		        "\"c\" : [ \"d\", \"e\" ], " \
			"\"f\" : [ { \"g\" : \"h\", \"i\" : \"j\" }, " \
			"          { \"k\" : \"l\", \"m\" : \"n\" }, " \
			"          { \"o\" : \"p\", \"q\" : \"r\" } ], " \
			"\"data\" : { \"child\" : [ { \"item\" : 1 } ] } " \
			"}";

/**
 * Simple literal path test
 */
TEST(LiterialJSONPathTest, JSON)
{
	string path("/a/b");
	JSONPath jpath(path);
	Document doc;
	doc.Parse(testdoc);
	Value& v = jpath.findNode(doc);
	ASSERT_TRUE(v.IsString());
}

/**
 * Simple index path test
 */
TEST(IndexJSONPath, JSON)
{
	string path("/c[0]");
	JSONPath jpath(path);
	Document doc;
	doc.Parse(testdoc);
	Value& v = jpath.findNode(doc);
	ASSERT_TRUE(v.IsString());
	ASSERT_EQ(0, strcmp(v.GetString(), "d"));
}

/**
 * Simple index path test with nested objects
 */
TEST(IndexIntJSONPath, JSON)
{
	string path("/data/child[0]/item");
	JSONPath jpath(path);
	Document doc;
	doc.Parse(testdoc);
	Value& v = jpath.findNode(doc);
	ASSERT_TRUE(v.IsInt());
	ASSERT_EQ(1, v.GetInt());
}


/**
 * Simple index path test
 */
TEST(MatchJSONPath, JSON)
{
	string path("/f[k==l]");
	JSONPath jpath(path);
	Document doc;
	doc.Parse(testdoc);
	Value& v = jpath.findNode(doc);
	ASSERT_TRUE(v.IsObject());
	ASSERT_TRUE(v.HasMember("k"));
	ASSERT_TRUE(v.HasMember("m"));
}


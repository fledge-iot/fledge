#include <gtest/gtest.h>
#include <string>
#include <vector>
#include "json_utils.h"

using namespace std;

const char *json_ok =  "{" \
				"\"errors400\":  "\
				        "["\
				                "\"Redefinition of the type with the same ID is not allowed\", "\
						"\"Invalid value type for the property\" "\
				        "]"\
				", " \
				"\"type\": \"JSON\", " \
				"\"order\": \"17\" ,"  \
				"\"readonly\": \"true\" " \
			"} ";

const char *json_bad_not_array =  "{" \
				"\"errors400\":  \"text\", " \
				"\"type\": \"JSON\", " \
				"\"order\": \"17\" ,"  \
				"\"readonly\": \"true\" " \
			"} ";

const char *json_bad =  "{" \
				"\"errors400\":  "\
				        "["\
				                "\"Redefinition of the type with the same ID is not allowed\", "\
						"\"Invalid value type for the property\" "\
				        "]"\
				", " \
				"xxxx";

TEST(JsonToVectorString, JSONok)
{
	std::vector<std::string> stringJSON;
	bool result;

	result = JSONStringToVectorString(stringJSON,json_ok,"errors400");

	ASSERT_EQ(result, true);
}

TEST(JsonToVectorString, KeyNotExist)
{
	std::vector<std::string> stringJSON;
	bool result;

	result = JSONStringToVectorString(stringJSON,json_ok,"xxx");

	ASSERT_EQ(result, false);
}

TEST(JsonToVectorString, NotArray)
{
	std::vector<std::string> stringJSON;
	bool result;

	result = JSONStringToVectorString(stringJSON,json_bad_not_array,"errors400");

	ASSERT_EQ(result, false);
}


TEST(JsonToVectorString, JSONbad)
{
	std::vector<std::string> stringJSON;
	bool result;

	result = JSONStringToVectorString(stringJSON,json_bad,"errors400");

	ASSERT_EQ(result, false);
}

TEST(JsonStringUnescape, LeadingAndTrailingDoubleQuote)
{
	string json = R"("value")";
	ASSERT_EQ("value", JSONunescape(json));
}

TEST(JsonStringUnescape, UnescapedDoubleQuote)
{
	string json = R"({\"key\":\"value\"})";
	ASSERT_EQ(R"({"key":"value"})", JSONunescape(json));
}

TEST(JsonStringUnescape, TwoTimesUnescapedDoubleQuote)
{
	string json = R"({\\"key\\":\\"value\\"})";
	ASSERT_EQ(R"({\"key\":\"value\"})", JSONunescape(json));
}

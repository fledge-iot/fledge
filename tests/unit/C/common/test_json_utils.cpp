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
TEST(JsonStringUnescape, ThreeTimesUnescapedDoubleQuote)
{
	string json = R"({\"key3\":\"_-_\\\"value3\\\"_-_\"})";
	ASSERT_EQ(R"({"key3":"_-_\"value3\"_-_"})", JSONunescape(json));
}
TEST(JsonStringUnescape, TwoTimesQuotedValue)
{
	string json = R"({\"key4\":\"\\"value4\\"\"})";
	ASSERT_EQ(R"({"key4":"\"value4\""})", JSONunescape(json));
}
TEST(JsonStringUnescape, DoubleQuotedValue)
{
	string json = R"({\"city\":\"\\\"Milan\\\"\"})";
	ASSERT_EQ(R"({"city":"\"Milan\""})", JSONunescape(json));
}

TEST(JsonStringUnescape, Backslash)
{
	// An escaped backslash must collapse to a single backslash
	string json = R"("ns=2;s=[Prog]Global\\Tag")";
	ASSERT_EQ(R"(ns=2;s=[Prog]Global\Tag)", JSONunescape(json));
}

TEST(JsonStringUnescape, BackslashBeforeN)
{
	// A backslash followed by the letter 'n' is escaped as backslash,
	// backslash, 'n' and must not be treated as a newline escape
	string json = R"("[Prog]Global\\node")";
	ASSERT_EQ(R"([Prog]Global\node)", JSONunescape(json));
}

TEST(JsonStringUnescape, NewlineEscape)
{
	string json = R"("line1\nline2")";
	ASSERT_EQ("line1\nline2", JSONunescape(json));
}

TEST(JsonStringUnescape, UnicodeEscapePreserved)
{
	// Unicode escapes are passed through for downstream JSON parsing
	string json = R"("snow\u2603man")";
	ASSERT_EQ(R"(snow\u2603man)", JSONunescape(json));
}

TEST(JsonStringEscape, Backslash)
{
	ASSERT_EQ(R"(ns=2;s=[Prog]Global\\Tag)", JSONescape(R"(ns=2;s=[Prog]Global\Tag)"));
}

TEST(JsonStringEscape, DoubleQuote)
{
	ASSERT_EQ(R"(say \"hi\")", JSONescape(R"(say "hi")"));
}

TEST(JsonStringEscape, ControlCharacters)
{
	ASSERT_EQ("line1\\nline2\\tend", JSONescape("line1\nline2\tend"));
}

TEST(JsonStringEscape, NoSpecialCharacters)
{
	ASSERT_EQ("plain text", JSONescape("plain text"));
}

TEST(JsonStringEscape, UnescapeRoundTrip)
{
	// JSONunescape must be the inverse of JSONescape
	string original = R"(ns=2;s=[Prog]Global\Tag with "quotes" and \new lines)";
	ASSERT_EQ(original, JSONunescape(JSONescape(original)));
}

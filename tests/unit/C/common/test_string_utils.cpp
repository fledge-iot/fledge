#include <gtest/gtest.h>
#include <iostream>
#include <string>
#include "string_utils.h"
#include <vector>

using namespace std;

class Row  {
	public:
		string v1;
		string v2;
		string v3;
		string v4;

		Row(const char *p1, const char *p2, const char *p3, const char *p4) {
			v1 = p1;
			v2 = p2;
			v3 = p3;
			v4 = p4;
		};
};

class StringUtilsTestClass : public ::testing::TestWithParam<Row> {
};

TEST(StringSlashFixTestClass, goodCases)
{
	vector<pair<string, string>> testCases = {

		// TestCase        - Expected
		{"foglamp_test1",    "foglamp_test1"},

		{"/foglamp_test1",   "foglamp_test1"},
		{"//foglamp_test1",  "foglamp_test1"},
		{"///foglamp_test1", "foglamp_test1"},

		{"foglamp_test1/",   "foglamp_test1"},
		{"foglamp_test1//",  "foglamp_test1"},
		{"foglamp_test1///", "foglamp_test1"},

		{"/a//b/c/",         "a/b/c"},
		{"foglamp/test1",    "foglamp/test1"},
		{"foglamp//test1",   "foglamp/test1"},
		{"foglamp//test//1", "foglamp/test/1"},

		{"//foglamp_test1//",    "foglamp_test1"},
		{"//foglamp//test//1//", "foglamp/test/1"}
	};
	string result;

	for(auto &testCase : testCases)
	{
		result = StringSlashFix(testCase.first);
		ASSERT_EQ(result, testCase.second);
	}
}


TEST(StringReplaceAllTestClass, goodCases)
{
	vector<std::tuple<string, string, string, string>> testCases = {

		// TestCase               - to search - to repplace   - Expected
		{std::make_tuple("foglamp@@test1",        "@@",       "@",            "foglamp@test1")},
		{std::make_tuple("foglamp@@test@@2",      "@@",       "@",            "foglamp@test@2")},
		{std::make_tuple("@@foglamp@@test@@3@@",  "@@",       "@",            "@foglamp@test@3@")}
	};
	string test;
	string toSearch;
	string toReplace;
	string Expected;

	for(auto &testCase : testCases)
	{
		test = std::get<0>(testCase);
		toSearch = std::get<1>(testCase);
		toReplace = std::get<2>(testCase);
		Expected = std::get<3>(testCase);

		StringReplaceAll(test, toSearch, toReplace);
		ASSERT_EQ(test, Expected);
	}
}



// Test Code
TEST_P(StringUtilsTestClass, StringUtilsTestCase)
{
	Row const& p = GetParam();

	string StringToManage = p.v1;
	string StringToSearch = p.v2;
	string StringReplacement = p.v3;
	string StringReplaced = p.v4;

	StringReplace(StringToManage, StringToSearch ,StringReplacement);

	ASSERT_EQ(StringToManage, StringReplaced);
}

INSTANTIATE_TEST_CASE_P(
	StringUtilsTestCase,
	StringUtilsTestClass,
	::testing::Values(
		//  To manage		Search		Replace		Expected
		Row("a XX XX",		"a",		"b",		"b XX XX"),
		Row("XX a XX",		"a",		"b",		"XX b XX"),
		Row("XX XX a",		"a",		"b",		"XX XX b"),

		Row("XX XX",		"a",		"b",		"XX XX"),

		Row("XX a a XX",	"a",		"b",		"XX b a XX")
	)
);

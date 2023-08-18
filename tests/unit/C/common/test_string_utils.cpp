#include <gtest/gtest.h>
#include <iostream>
#include <string>
#include "string_utils.h"
#include <vector>
#include <bits/stdc++.h>
#include <regex>

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
		{"fledge_test1",    "fledge_test1"},

		{"/fledge_test1",   "fledge_test1"},
		{"//fledge_test1",  "fledge_test1"},
		{"///fledge_test1", "fledge_test1"},

		{"fledge_test1/",   "fledge_test1"},
		{"fledge_test1//",  "fledge_test1"},
		{"fledge_test1///", "fledge_test1"},

		{"/a//b/c/",         "a/b/c"},
		{"fledge/test1",    "fledge/test1"},
		{"fledge//test1",   "fledge/test1"},
		{"fledge//test//1", "fledge/test/1"},

		{"//fledge_test1//",    "fledge_test1"},
		{"//fledge//test//1//", "fledge/test/1"}
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
		{std::make_tuple("fledge@@test1",        "@@",       "@",            "fledge@test1")},
		{std::make_tuple("fledge@@test@@2",      "@@",       "@",            "fledge@test@2")},
		{std::make_tuple("@@fledge@@test@@3@@",  "@@",       "@",            "@fledge@test@3@")}
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


// Test String trim
TEST(StringTrim, StringTrimCases)
{
	ASSERT_EQ(StringRTrim("xxx") , "xxx");
	ASSERT_EQ(StringRTrim("xxx "), "xxx");
	ASSERT_EQ(StringRTrim("xxx   "), "xxx");

	ASSERT_EQ(StringLTrim("xxx"), "xxx");
	ASSERT_EQ(StringLTrim(" xxx"), "xxx");
	ASSERT_EQ(StringLTrim("  xxx"), "xxx");

	ASSERT_EQ(StringTrim("xxx"), "xxx");
	ASSERT_EQ(StringTrim("  xxx"), "xxx");
	ASSERT_EQ(StringTrim("xxx  "), "xxx");
	ASSERT_EQ(StringTrim("  xxx  "), "xxx");
}

// Test StringStripWhiteSpacesAll
TEST(StringStripWhiteSpacesAll, AllCases)
{
	ASSERT_EQ(StringStripWhiteSpacesAll("xxx") , "xxx");

	ASSERT_EQ(StringStripWhiteSpacesAll(" xxx") , "xxx");
	ASSERT_EQ(StringStripWhiteSpacesAll(" xxx ") , "xxx");

	ASSERT_EQ(StringStripWhiteSpacesAll(" x x x ") , "xxx");

	ASSERT_EQ(StringStripWhiteSpacesAll("Messages:[  {   MessageIndex:0") , "Messages:[{MessageIndex:0");

	ASSERT_EQ(StringStripWhiteSpacesAll(" x x x ") , "xxx");

	ASSERT_EQ(StringStripWhiteSpacesAll(" x x\tx ") , "xxx");
	ASSERT_EQ(StringStripWhiteSpacesAll(" x x\nx ") , "xxx");
	ASSERT_EQ(StringStripWhiteSpacesAll(" x x\vx ") , "xxx");
	ASSERT_EQ(StringStripWhiteSpacesAll(" x x\fx ") , "xxx");
	ASSERT_EQ(StringStripWhiteSpacesAll(" x x\rx ") , "xxx");

}

// Test StringStripWhiteSpacesAll
TEST(StringStripWhiteSpacesLeave1Space, AllCases)
{
	ASSERT_EQ(StringStripWhiteSpacesExtra("xxx") , "xxx");

	ASSERT_EQ(StringStripWhiteSpacesExtra(" xxx") , "xxx");

	ASSERT_EQ(StringStripWhiteSpacesExtra(" xxx ") , "xxx");

	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x x ") , "x x x");

	ASSERT_EQ(StringStripWhiteSpacesExtra(" x  x   x ") , "x x x");

	ASSERT_EQ(StringStripWhiteSpacesExtra("Messages:[  {   MessageIndex:0") , "Messages:[ { MessageIndex:0");

	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x\tx ") , "x xx");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x\nx ") , "x xx");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x\vx ") , "x xx");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x\fx ") , "x xx");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x\rx ") , "x xx");

	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x\tx ") , "x xx");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x\n x ") , "x x x");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x\v  x ") , "x x x");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x\f   x ") , "x x x");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x\r    x ") , "x x x");

	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x \tx ") , "x x x");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x  \n x ") , "x x x");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x  \v  x ") , "x x x");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x  \f   x ") , "x x x");
	ASSERT_EQ(StringStripWhiteSpacesExtra(" x x  \r    x ") , "x x x");
}

// Some tests are skipped on Centos
// Centos 7.0 has gcc 4.8.5, <regex> was implemented and released in GCC 4.9.0.
// the version available in C7 was highly experimental.
//
// Test IsRegex
TEST(TestIsRegex, AllCases)
{
	ASSERT_EQ(IsRegex("^a") , true);
	ASSERT_EQ(IsRegex(".*") , true);
	ASSERT_EQ(IsRegex("\\s") , true);
	ASSERT_EQ(IsRegex("^.*(Code:)((?!2).)*$") , true);

	ASSERT_EQ(IsRegex("asset_1") , false);

	ASSERT_EQ(std::regex_match ("sin_1_asset_1", regex("^a")), false);

#ifndef RHEL_CENTOS_7
	ASSERT_EQ(std::regex_match ("sin_1_asset_1", regex("^s.*")), true);
#endif

	ASSERT_EQ(std::regex_match ("sin_1_asset_1", regex("a.*")), false);
	ASSERT_EQ(std::regex_match ("sin_1_asset_1", regex("s.*")), true);
}



TEST(TestAround, Extract)
{
	string longString("not shownpreamble123This part is after the location");
	string s = StringAround(longString, 19);
	EXPECT_STREQ(s.c_str(), "preamble123This part is after the locati");
	s = StringAround(longString, 19, 10);
	EXPECT_STREQ(s.c_str(), "preamble123This part");
	s = StringAround(longString, 19, 10, 5);
	EXPECT_STREQ(s.c_str(), "ble123This part");
	s = StringAround(longString, 5);
	EXPECT_STREQ(s.c_str(), "not shownpreamble123This part is after t");
}

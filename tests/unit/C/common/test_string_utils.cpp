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

// URL Encoding/Decoding Tests
TEST(UrlEncodeTest, BasicCases)
{
	ASSERT_EQ(urlEncode("hello world"), "hello%20world");
	ASSERT_EQ(urlEncode("hello+world"), "hello%2Bworld");
	ASSERT_EQ(urlEncode("hello/world"), "hello%2Fworld");
	ASSERT_EQ(urlEncode("hello&world"), "hello%26world");
	ASSERT_EQ(urlEncode("hello=world"), "hello%3Dworld");
	ASSERT_EQ(urlEncode("hello@world"), "hello%40world");
	ASSERT_EQ(urlEncode("hello:world"), "hello%3Aworld");
	ASSERT_EQ(urlEncode("hello;world"), "hello%3Bworld");
	ASSERT_EQ(urlEncode("hello,world"), "hello%2Cworld");
	ASSERT_EQ(urlEncode("hello?world"), "hello%3Fworld");
	ASSERT_EQ(urlEncode("hello#world"), "hello%23world");
	ASSERT_EQ(urlEncode("hello[world"), "hello%5Bworld");
	ASSERT_EQ(urlEncode("hello]world"), "hello%5Dworld");
	ASSERT_EQ(urlEncode("hello{world"), "hello%7Bworld");
	ASSERT_EQ(urlEncode("hello}world"), "hello%7Dworld");
	ASSERT_EQ(urlEncode("hello|world"), "hello%7Cworld");
	ASSERT_EQ(urlEncode("hello\\world"), "hello%5Cworld");
	ASSERT_EQ(urlEncode("hello^world"), "hello%5Eworld");
	ASSERT_EQ(urlEncode("hello`world"), "hello%60world");
	ASSERT_EQ(urlEncode("hello~world"), "hello~world");
	ASSERT_EQ(urlEncode("hello\"world"), "hello%22world");
	ASSERT_EQ(urlEncode("hello'world"), "hello%27world");
	ASSERT_EQ(urlEncode("hello<world"), "hello%3Cworld");
	ASSERT_EQ(urlEncode("hello>world"), "hello%3Eworld");
	ASSERT_EQ(urlEncode("hello%world"), "hello%25world");
	ASSERT_EQ(urlEncode("hello$world"), "hello%24world");
	ASSERT_EQ(urlEncode("hello!world"), "hello%21world");
	ASSERT_EQ(urlEncode("hello*world"), "hello%2Aworld");
	ASSERT_EQ(urlEncode("hello(world"), "hello%28world");
	ASSERT_EQ(urlEncode("hello)world"), "hello%29world");
	ASSERT_EQ(urlEncode("hello_world"), "hello_world"); // Should remain unchanged
	ASSERT_EQ(urlEncode("hello-world"), "hello-world"); // Should remain unchanged
	ASSERT_EQ(urlEncode("hello.world"), "hello.world"); // Should remain unchanged
	ASSERT_EQ(urlEncode(""), ""); // Empty string
	ASSERT_EQ(urlEncode("abc123"), "abc123"); // Alphanumeric should remain unchanged
}

TEST(UrlDecodeTest, BasicCases)
{
	ASSERT_EQ(urlDecode("hello%20world"), "hello world");
	ASSERT_EQ(urlDecode("hello+world"), "hello world");
	ASSERT_EQ(urlDecode("hello%2Bworld"), "hello+world");
	ASSERT_EQ(urlDecode("hello%2Fworld"), "hello/world");
	ASSERT_EQ(urlDecode("hello%26world"), "hello&world");
	ASSERT_EQ(urlDecode("hello%3Dworld"), "hello=world");
	ASSERT_EQ(urlDecode("hello%40world"), "hello@world");
	ASSERT_EQ(urlDecode("hello%3Aworld"), "hello:world");
	ASSERT_EQ(urlDecode("hello%3Bworld"), "hello;world");
	ASSERT_EQ(urlDecode("hello%2Cworld"), "hello,world");
	ASSERT_EQ(urlDecode("hello%3Fworld"), "hello?world");
	ASSERT_EQ(urlDecode("hello%23world"), "hello#world");
	ASSERT_EQ(urlDecode("hello%5Bworld"), "hello[world");
	ASSERT_EQ(urlDecode("hello%5Dworld"), "hello]world");
	ASSERT_EQ(urlDecode("hello%7Bworld"), "hello{world");
	ASSERT_EQ(urlDecode("hello%7Dworld"), "hello}world");
	ASSERT_EQ(urlDecode("hello%7Cworld"), "hello|world");
	ASSERT_EQ(urlDecode("hello%5Cworld"), "hello\\world");
	ASSERT_EQ(urlDecode("hello%5Eworld"), "hello^world");
	ASSERT_EQ(urlDecode("hello%60world"), "hello`world");
	ASSERT_EQ(urlDecode("hello%7Eworld"), "hello~world");
	ASSERT_EQ(urlDecode("hello%22world"), "hello\"world");
	ASSERT_EQ(urlDecode("hello%27world"), "hello'world");
	ASSERT_EQ(urlDecode("hello%3Cworld"), "hello<world");
	ASSERT_EQ(urlDecode("hello%3Eworld"), "hello>world");
	ASSERT_EQ(urlDecode("hello%25world"), "hello%world");
	ASSERT_EQ(urlDecode("hello%24world"), "hello$world");
	ASSERT_EQ(urlDecode("hello%21world"), "hello!world");
	ASSERT_EQ(urlDecode("hello%2Aworld"), "hello*world");
	ASSERT_EQ(urlDecode("hello%28world"), "hello(world");
	ASSERT_EQ(urlDecode("hello%29world"), "hello)world");
	ASSERT_EQ(urlDecode("hello_world"), "hello_world"); // Should remain unchanged
	ASSERT_EQ(urlDecode("hello-world"), "hello-world"); // Should remain unchanged
	ASSERT_EQ(urlDecode("hello.world"), "hello.world"); // Should remain unchanged
	ASSERT_EQ(urlDecode(""), ""); // Empty string
	ASSERT_EQ(urlDecode("abc123"), "abc123"); // Alphanumeric should remain unchanged
}

TEST(UrlEncodeDecodeTest, RoundTrip)
{
	vector<string> testStrings = {
		"hello world",
		"hello+world",
		"hello/world",
		"hello&world",
		"hello=world",
		"hello@world",
		"hello:world",
		"hello;world",
		"hello,world",
		"hello?world",
		"hello#world",
		"hello[world",
		"hello]world",
		"hello{world",
		"hello}world",
		"hello|world",
		"hello\\world",
		"hello^world",
		"hello`world",
		"hello~world",
		"hello\"world",
		"hello'world",
		"hello<world",
		"hello>world",
		"hello%world",
		"hello$world",
		"hello!world",
		"hello*world",
		"hello(world",
		"hello)world",
		"hello_world",
		"hello-world",
		"hello.world",
		"abc123",
		"",
		"special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
	};
	
	for (const auto& original : testStrings) {
		string encoded = urlEncode(original);
		string decoded = urlDecode(encoded);
		ASSERT_EQ(decoded, original) << "Round trip failed for: " << original;
	}
}

// Path Manipulation Tests
TEST(EvaluateParentPathTest, BasicCases)
{
	ASSERT_EQ(evaluateParentPath("/a/b/c", '/'), "/a/b");
	ASSERT_EQ(evaluateParentPath("/a/b/", '/'), "/a/b");
	ASSERT_EQ(evaluateParentPath("/a/b", '/'), "/a");
	ASSERT_EQ(evaluateParentPath("/a/", '/'), "/a");
	ASSERT_EQ(evaluateParentPath("/", '/'), "/");
	ASSERT_EQ(evaluateParentPath("a/b/c", '/'), "a/b");
	ASSERT_EQ(evaluateParentPath("a/b/", '/'), "a/b");
	ASSERT_EQ(evaluateParentPath("a/b", '/'), "a");
	ASSERT_EQ(evaluateParentPath("a/", '/'), "a");
	ASSERT_EQ(evaluateParentPath("a", '/'), "a");
	ASSERT_EQ(evaluateParentPath("", '/'), "");
	ASSERT_EQ(evaluateParentPath("abc", '/'), "abc");
	
	// Test with different separators
	ASSERT_EQ(evaluateParentPath("a\\b\\c", '\\'), "a\\b");
	ASSERT_EQ(evaluateParentPath("a.b.c", '.'), "a.b");
}

TEST(ExtractLastLevelTest, BasicCases)
{
	ASSERT_EQ(extractLastLevel("/a/b/c", '/'), "c");
	ASSERT_EQ(extractLastLevel("/a/b/", '/'), "");
	ASSERT_EQ(extractLastLevel("/a/b", '/'), "b");
	ASSERT_EQ(extractLastLevel("/a/", '/'), "");
	ASSERT_EQ(extractLastLevel("/a", '/'), "a");
	ASSERT_EQ(extractLastLevel("/", '/'), "");
	ASSERT_EQ(extractLastLevel("a/b/c", '/'), "c");
	ASSERT_EQ(extractLastLevel("a/b/", '/'), "");
	ASSERT_EQ(extractLastLevel("a/b", '/'), "b");
	ASSERT_EQ(extractLastLevel("a/", '/'), "");
	ASSERT_EQ(extractLastLevel("a", '/'), "a");
	ASSERT_EQ(extractLastLevel("", '/'), "");
	ASSERT_EQ(extractLastLevel("abc", '/'), "abc");
	
	// Test with different separators
	ASSERT_EQ(extractLastLevel("a\\b\\c", '\\'), "c");
	ASSERT_EQ(extractLastLevel("a.b.c", '.'), "c");
	ASSERT_EQ(extractLastLevel("a-b-c", '-'), "c");
}

// String Stripping Tests
TEST(StringStripCRLFTest, BasicCases)
{
	string test1 = "hello\r\nworld";
	StringStripCRLF(test1);
	ASSERT_EQ(test1, "helloworld");
	
	string test2 = "hello\rworld";
	StringStripCRLF(test2);
	ASSERT_EQ(test2, "helloworld");
	
	string test3 = "hello\nworld";
	StringStripCRLF(test3);
	ASSERT_EQ(test3, "helloworld");
	
	string test4 = "hello\r\n\r\nworld";
	StringStripCRLF(test4);
	ASSERT_EQ(test4, "helloworld");
	
	string test5 = "hello world";
	StringStripCRLF(test5);
	ASSERT_EQ(test5, "hello world");
	
	string test6 = "";
	StringStripCRLF(test6);
	ASSERT_EQ(test6, "");
}

TEST(StringStripQuotesTest, BasicCases)
{
	string test1 = "\"hello world\"";
	StringStripQuotes(test1);
	ASSERT_EQ(test1, "hello world");
	
	string test2 = "hello \"world\"";
	StringStripQuotes(test2);
	ASSERT_EQ(test2, "hello world");
	
	string test3 = "\"hello\" \"world\"";
	StringStripQuotes(test3);
	ASSERT_EQ(test3, "hello world");
	
	string test4 = "hello world";
	StringStripQuotes(test4);
	ASSERT_EQ(test4, "hello world");
	
	string test5 = "";
	StringStripQuotes(test5);
	ASSERT_EQ(test5, "");
	
	string test6 = "\"\"";
	StringStripQuotes(test6);
	ASSERT_EQ(test6, "");
}

// String Escape Tests
TEST(StringEscapeQuotesTest, BasicCases)
{
	string test1 = "hello \"world\"";
	StringEscapeQuotes(test1);
	ASSERT_EQ(test1, "hello \\\"world\\\"");
	
	string test2 = "\"hello world\"";
	StringEscapeQuotes(test2);
	ASSERT_EQ(test2, "\\\"hello world\\\"");
	
	string test3 = "hello world";
	StringEscapeQuotes(test3);
	ASSERT_EQ(test3, "hello world");
	
	string test4 = "hello\\\"world";
	StringEscapeQuotes(test4);
	ASSERT_EQ(test4, "hello\\\"world"); // Already escaped
	
	string test5 = "";
	StringEscapeQuotes(test5);
	ASSERT_EQ(test5, "");
	
	string test6 = "\"";
	StringEscapeQuotes(test6);
	ASSERT_EQ(test6, "\\\"");
}

TEST(EscapeTest, BasicCases)
{
	ASSERT_EQ(escape("hello world"), "hello world");
	ASSERT_EQ(escape("hello \"world\""), "hello \\\"world\\\"");
	ASSERT_EQ(escape("hello \\world"), "hello \\\\world");
	ASSERT_EQ(escape("hello /world"), "hello /world");
	ASSERT_EQ(escape("hello \"world\" \\test /path"), "hello \\\"world\\\" \\\\test /path");
	ASSERT_EQ(escape(""), "");
	ASSERT_EQ(escape("no_special_chars"), "no_special_chars");
	ASSERT_EQ(escape("\\"), "\\\\");
	ASSERT_EQ(escape("\""), "\\\"");
	ASSERT_EQ(escape("/"), "/");
	ASSERT_EQ(escape("\\\""), "\\\""); // Already escaped
	ASSERT_EQ(escape("\\/"), "\\/"); // Already escaped
}

// String Replace All Ex Tests
TEST(StringReplaceAllExTest, BasicCases)
{
	string test1 = "hello world hello";
	StringReplaceAllEx(test1, "hello", "hi");
	ASSERT_EQ(test1, "hi world hi");
	
	string test2 = "hello hello hello";
	StringReplaceAllEx(test2, "hello", "hi");
	ASSERT_EQ(test2, "hi hi hi");
	
	string test3 = "hello world";
	StringReplaceAllEx(test3, "hello", "hi");
	ASSERT_EQ(test3, "hi world");
	
	string test4 = "hello world";
	StringReplaceAllEx(test4, "world", "earth");
	ASSERT_EQ(test4, "hello earth");
	
	string test5 = "hello world";
	StringReplaceAllEx(test5, "xyz", "abc");
	ASSERT_EQ(test5, "hello world"); // No change
	
	string test6 = "";
	StringReplaceAllEx(test6, "hello", "hi");
	ASSERT_EQ(test6, "");
	
	string test7 = "hello";
	StringReplaceAllEx(test7, "hello", "");
	ASSERT_EQ(test7, "");
	
	string test8 = "hellohello";
	StringReplaceAllEx(test8, "hello", "hi");
	ASSERT_EQ(test8, "hihi");
}

// Trim Function Tests (C-style)
TEST(TrimTest, BasicCases)
{
	char test1[] = "  hello world  ";
	char* result1 = trim(test1);
	ASSERT_STREQ(result1, "hello world");
	
	char test2[] = "hello world";
	char* result2 = trim(test2);
	ASSERT_STREQ(result2, "hello world");
	
	char test3[] = "  hello world";
	char* result3 = trim(test3);
	ASSERT_STREQ(result3, "hello world");
	
	char test4[] = "hello world  ";
	char* result4 = trim(test4);
	ASSERT_STREQ(result4, "hello world");
	
	char test5[] = "   ";
	char* result5 = trim(test5);
	ASSERT_STREQ(result5, "");
	
	char test6[] = "";
	char* result6 = trim(test6);
	ASSERT_STREQ(result6, "");
	
	char test7[] = "hello";
	char* result7 = trim(test7);
	ASSERT_STREQ(result7, "hello");
}

// Edge Cases and Error Conditions
TEST(StringUtilsEdgeCases, EmptyAndNullCases)
{
	// Test empty strings
	string empty = "";
	ASSERT_EQ(StringSlashFix(empty), "");
	ASSERT_EQ(evaluateParentPath(empty, '/'), "");
	ASSERT_EQ(extractLastLevel(empty, '/'), "");
	ASSERT_EQ(StringStripWhiteSpacesAll(empty), "");
	ASSERT_EQ(StringStripWhiteSpacesExtra(empty), "");
	ASSERT_EQ(urlEncode(empty), "");
	ASSERT_EQ(urlDecode(empty), "");
	ASSERT_EQ(StringLTrim(empty), "");
	ASSERT_EQ(StringRTrim(empty), "");
	ASSERT_EQ(StringTrim(empty), "");
	ASSERT_EQ(escape(empty), "");
	
	// Test single character strings
	ASSERT_EQ(StringSlashFix("/"), "");
	ASSERT_EQ(StringSlashFix("a"), "a");
	ASSERT_EQ(evaluateParentPath("/", '/'), "/");
	ASSERT_EQ(evaluateParentPath("a", '/'), "a");
	ASSERT_EQ(extractLastLevel("/", '/'), "");
	ASSERT_EQ(extractLastLevel("a", '/'), "a");
}

TEST(StringUtilsBoundaryCases, BoundaryConditions)
{
	// Test very long strings
	string longString(1000, 'a');
	ASSERT_EQ(StringStripWhiteSpacesAll(longString), longString);
	
	// Test strings with only special characters
	ASSERT_EQ(urlEncode("!@#$%^&*()"), "%21%40%23%24%25%5E%26%2A%28%29");
	
	// Test strings with mixed content
	string mixed = "Hello World 123 !@#";
	ASSERT_EQ(StringStripWhiteSpacesAll(mixed), "HelloWorld123!@#");
	ASSERT_EQ(StringStripWhiteSpacesExtra(mixed), "Hello World 123 !@#");
}

// Additional comprehensive tests for existing functions
TEST(StringReplaceAllTest, AdditionalCases)
{
	string test1 = "hello world hello world";
	StringReplaceAll(test1, "hello", "hi");
	ASSERT_EQ(test1, "hi world hi world");
	
	string test2 = "hello";
	StringReplaceAll(test2, "hello", "hi");
	ASSERT_EQ(test2, "hi");
	
	string test3 = "hello";
	StringReplaceAll(test3, "world", "earth");
	ASSERT_EQ(test3, "hello"); // No change
	
	string test4 = "hellohello";
	StringReplaceAll(test4, "hello", "hi");
	ASSERT_EQ(test4, "hihi");
	
	string test5 = "";
	StringReplaceAll(test5, "hello", "hi");
	ASSERT_EQ(test5, "");
	
	string test6 = "hello";
	StringReplaceAll(test6, "hello", "");
	ASSERT_EQ(test6, "");
}

TEST(StringAroundTest, AdditionalCases)
{
	string testString = "abcdefghijklmnopqrstuvwxyz";
	
	// Test boundary conditions
	ASSERT_EQ(StringAround(testString, 0, 5, 0), "abcde");
	ASSERT_EQ(StringAround(testString, 25, 5, 5), "uvwxyz");
	ASSERT_EQ(StringAround(testString, 13, 10, 10), "defghijklmnopqrstuvw");
	
	// Test with position beyond string length
	ASSERT_EQ(StringAround(testString, 30, 5, 5), "z");
	
	// Test with empty string
	ASSERT_EQ(StringAround("", 0, 5, 5), "");
	
	// Test with short string
	ASSERT_EQ(StringAround("abc", 1, 5, 5), "abc");
}

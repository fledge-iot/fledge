#include <gtest/gtest.h>
#include <iostream>
#include <string>
#include "string_utils.h"

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

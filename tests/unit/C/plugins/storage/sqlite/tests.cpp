#include <gtest/gtest.h>
#include <connection.h>
#include <logger.h>
#include <string.h>
#include <string>
#include <readings_catalogue.h>

using namespace std;

int main(int argc, char **argv) {
    testing::InitGoogleTest(&argc, argv);

    testing::GTEST_FLAG(repeat) = 1;
    testing::GTEST_FLAG(shuffle) = true;
    testing::GTEST_FLAG(death_test_style) = "threadsafe";

    return RUN_ALL_TESTS();
}


TEST(MultiReadings, extractReadingsIdFromName) {

	ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();

	ASSERT_EQ(readCat->extractReadingsIdFromName("reading_1_1"), 1);
	ASSERT_EQ(readCat->extractReadingsIdFromName("reading_2_1"), 1);
	ASSERT_EQ(readCat->extractReadingsIdFromName("reading_10_1"), 1);
	ASSERT_EQ(readCat->extractReadingsIdFromName("reading_60_1"), 1);

	ASSERT_EQ(readCat->extractReadingsIdFromName("reading_1_10"), 10);
	ASSERT_EQ(readCat->extractReadingsIdFromName("reading_1_100"), 100);
	ASSERT_EQ(readCat->extractReadingsIdFromName("reading_10_100"), 100);
	ASSERT_EQ(readCat->extractReadingsIdFromName("reading_60_100"), 100);
}

TEST(MultiReadings, extractDbIdFromName) {

	ReadingsCatalogue *readCat = ReadingsCatalogue::getInstance();

	ASSERT_EQ(readCat->extractDbIdFromName("reading_1_1"), 1);
	ASSERT_EQ(readCat->extractDbIdFromName("reading_2_1"), 2);
	ASSERT_EQ(readCat->extractDbIdFromName("reading_10_1"), 10);
	ASSERT_EQ(readCat->extractDbIdFromName("reading_60_1"), 60);

	ASSERT_EQ(readCat->extractDbIdFromName("reading_1_10"), 1);
	ASSERT_EQ(readCat->extractDbIdFromName("reading_1_100"), 1);
	ASSERT_EQ(readCat->extractDbIdFromName("reading_10_100"), 10);
	ASSERT_EQ(readCat->extractDbIdFromName("reading_60_100"), 60);
}

class RowFormatDate  {
	public:
		const char *test_case;
		const char *expected;
		bool result;

		RowFormatDate(const char *p1, const char *p2, bool p3) {
			test_case = p1;
			expected = p2;
			result = p3;
		};
};

class TestFormatDate : public ::testing::TestWithParam<RowFormatDate> {
};

TEST_P(TestFormatDate, TestConversions)
{
EXPECT_EXIT({
	Connection a;
	Logger::getLogger()->setMinLevel("debug");

	RowFormatDate const& p = GetParam();

	char formatted_date[50] = {0};
	memset (formatted_date,0 , sizeof (formatted_date));
	bool result  = a.formatDate(formatted_date, sizeof(formatted_date), p.test_case);

	string test_case = formatted_date;
	string expected = p.expected;

	bool ret = test_case.compare(expected) == 0;
	if (!ret)
	{
		cerr << "TestConversions doesn't return expected value" << endl;
		exit(1);
	}
	ret = result == p.result;
	exit(!ret); }, ::testing::ExitedWithCode(0), "");
}

INSTANTIATE_TEST_CASE_P(
	TestConversions,
	TestFormatDate,
	::testing::Values(
		// Test cases                                      Expected
		RowFormatDate("2019-01-01 10:01:01"              ,"2019-01-01 10:01:01.000000+00:00", true),
		RowFormatDate("2019-02-01 10:02:01.0"            ,"2019-02-01 10:02:01.000000+00:00", true),
		RowFormatDate("2019-02-02 10:02:02.841"          ,"2019-02-02 10:02:02.841000+00:00", true),
		RowFormatDate("2019-02-03 10:02:03.123456"       ,"2019-02-03 10:02:03.123456+00:00", true),

		RowFormatDate("2019-03-01 10:03:01.1+00:00"      ,"2019-03-01 10:03:01.100000+00:00", true),
		RowFormatDate("2019-03-02 10:03:02.123+00:00"    ,"2019-03-02 10:03:02.123000+00:00", true),

		RowFormatDate("2019-03-03 10:03:03.123456+00:00" ,"2019-03-03 10:03:03.123456+00:00", true),
		RowFormatDate("2019-03-04 10:03:04.123456+01:00" ,"2019-03-04 10:03:04.123456+01:00", true),
		RowFormatDate("2019-03-05 10:03:05.123456-01:00" ,"2019-03-05 10:03:05.123456-01:00", true),
		RowFormatDate("2019-03-04 10:03:04.123456+02:30" ,"2019-03-04 10:03:04.123456+02:30", true),
		RowFormatDate("2019-03-05 10:03:05.123456-02:30" ,"2019-03-05 10:03:05.123456-02:30", true),

		// Timestamp truncated
		RowFormatDate("2017-10-11 15:10:51.927191906"    ,"2017-10-11 15:10:51.927191+00:00", true),

		// Bad cases
		RowFormatDate("xxx",                    "", false),
		RowFormatDate("2019-50-50 10:01:01.0",  "", false)
	)
);

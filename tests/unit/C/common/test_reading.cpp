#include <gtest/gtest.h>
#include <reading.h>
#include <string.h>
#include <string>

using namespace std;

int main(int argc, char **argv) {
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}

TEST(ReadingTest, IntValue)
{
	DatapointValue value(10);
	Reading reading(string("test1"), new Datapoint("x", value));
	string json = reading.toJSON();
	ASSERT_NE(json.find(string("\"asset_code\" : \"test1\"")), 0);
	ASSERT_NE(json.find(string("\"reading\" : { \"x\" : \"10\" }")), 0);
	ASSERT_NE(json.find(string("\"readkey\" : ")), 0);
	ASSERT_NE(json.find(string("\"ser_ts\" : ")), 0);
}



#include <gtest/gtest.h>
#include <connection.h>
#include "gtest/gtest.h"
#include <logger.h>
#include <string.h>
#include <string>

using namespace std;

int main(int argc, char **argv) {
    testing::InitGoogleTest(&argc, argv);

    testing::GTEST_FLAG(repeat) = 50;
    testing::GTEST_FLAG(shuffle) = true;
    testing::GTEST_FLAG(death_test_style) = "threadsafe";

    return RUN_ALL_TESTS();
}

TEST(Sqlitelb, dummy) {

	ASSERT_EQ(1, 1);
}

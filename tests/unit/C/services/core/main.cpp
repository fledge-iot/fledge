#include <gtest/gtest.h>
#include <resultset.h>
#include <string.h>
#include <string>

using namespace std;

int main(int argc, char **argv) {
    testing::InitGoogleTest(&argc, argv);

    testing::GTEST_FLAG(repeat) = 5000;
    testing::GTEST_FLAG(shuffle) = true;
    testing::GTEST_FLAG(break_on_failure) = true;

    return RUN_ALL_TESTS();
}


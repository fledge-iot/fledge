#include <gtest/gtest.h>
#include <configuration.h>
#include <string.h>
#include <string>
#include <stdlib.h>

using namespace std;


int main(int argc, char **argv) {

	// Select the proper storage.json file for the tests
	string foglamp_root = getenv("FOGLAMP_ROOT");
	string foglamp_data = foglamp_root + "/tests/unit/C/services/storage/postgres";

	setenv("FOGLAMP_DATA", foglamp_data.c_str(), 1 );

	testing::InitGoogleTest(&argc, argv);

	testing::GTEST_FLAG(repeat) = 1000;
	testing::GTEST_FLAG(shuffle) = true;
	testing::GTEST_FLAG(break_on_failure) = true;

	return RUN_ALL_TESTS();
}

/**
 * Test retrieval of port from default
 */
TEST(ConfigurationTest, getport)
{
	StorageConfiguration	conf;

	ASSERT_EQ(strcmp(conf.getValue(string("port")), "8080"), 0);
}

/**
 * Test retrieval of plugin from default
 */
TEST(ConfigurationTest, getplugin)
{
	StorageConfiguration	conf;

	ASSERT_EQ(strcmp(conf.getValue(string("plugin")), "postgres"), 0);
}

/**
 * Test setting of port
 */
TEST(ConfigurationTest, setport)
{
	StorageConfiguration	conf;

	ASSERT_EQ(true, conf.setValue(string("port"), string("8188")));
	ASSERT_EQ(strcmp(conf.getValue(string("port")), "8188"), 0);
}

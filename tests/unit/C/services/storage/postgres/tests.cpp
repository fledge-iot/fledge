#include <gtest/gtest.h>
#include <configuration.h>
#include <string.h>
#include <string>

using namespace std;

int main(int argc, char **argv) {
    testing::InitGoogleTest(&argc, argv);

    testing::GTEST_FLAG(repeat) = 1;
    testing::GTEST_FLAG(shuffle) = true;
    testing::GTEST_FLAG(break_on_failure) = true;

    return RUN_ALL_TESTS();
}

/**
 * Select the proper storage.json file for the tests
 */
void cache_file_select()
{

	string foglamp_root = getenv("FOGLAMP_ROOT");
	string foglamp_data = foglamp_root + "/tests/unit/C/services/storage/postgres";

	char buf[512];
	snprintf(buf, sizeof(buf), "FOGLAMP_DATA=%s", foglamp_data.c_str());
	putenv(buf);
}

/**
 * Test retrieval of port from default
 */
TEST(ConfigurationTest, getport)
{
	StorageConfiguration	conf;

	ASSERT_EQ(strcmp(conf.getValue(string("port")), "0"), 0);
}

/**
 * Test retrieval of plugin from default
 */
TEST(ConfigurationTest, getplugin)
{
	cache_file_select();

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

#include <gtest/gtest.h>
#include <configuration.h>
#include <string.h>
#include <string>

using namespace std;

int main(int argc, char **argv) {
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
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

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

	testing::GTEST_FLAG(repeat) = 250;
	testing::GTEST_FLAG(shuffle) = true;
	testing::GTEST_FLAG(death_test_style) = "threadsafe";

	return RUN_ALL_TESTS();
}

/**
 * Test retrieval of port from default
 */
TEST(ConfigurationTest, getport)
{
EXPECT_EXIT({
	StorageConfiguration	conf;

	bool ret = strcmp(conf.getValue(string("port")), "8080") == 0;
	if (!ret)
	{
		cerr << "port value is not 8080" << endl;
	}
	exit(!(ret == true)); }, ::testing::ExitedWithCode(0), "");
}

/**
 * Test retrieval of plugin from default
 */
TEST(ConfigurationTest, getplugin)
{
EXPECT_EXIT({
	StorageConfiguration	conf;

	bool ret = strcmp(conf.getValue(string("plugin")), "postgres") == 0;
	if (!ret)
	{
		cerr << "plugin value is not 'postgres'" << endl;
	}
	exit(!(ret == true)); }, ::testing::ExitedWithCode(0), "");
}

/**
 * Test setting of port
 */
TEST(ConfigurationTest, setport)
{
EXPECT_EXIT({
	StorageConfiguration	conf;

	bool ret = conf.setValue(string("port"), string("8188"));
	if (!ret)
	{
		cerr << "Failed to set port value to 8188" << endl;
		exit(1);
	}
	ret = strcmp(conf.getValue(string("port")), "8188") == 0;
	if (!ret)
	{
		cerr << "Port value retrieved is not 8188" << endl;	
	}
	exit(!(ret == true)); }, ::testing::ExitedWithCode(0), "");
}

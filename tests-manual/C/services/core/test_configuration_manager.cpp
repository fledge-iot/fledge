#include <gtest/gtest.h>
#include <configuration_manager.h>
#include <rapidjson/document.h>

using namespace std;
using namespace rapidjson;

// Get all found category names and description
TEST(ConfigurationManagerTest, getAllCategoryNames)
{
	// Before the test start the storage layer with FOGLAMP_DATA=.
	// TCP port will be 8080
	ConfigurationManager *cfgManager = ConfigurationManager::getInstance("127.0.0.1", 8080);

	ConfigCategories allCats = cfgManager->getAllCategoryNames();

	string result = "{\"categories\": " + allCats.toJSON() + "}";

	Document doc;
	doc.Parse(result.c_str());

	if (doc.HasParseError() || !doc.HasMember("categories"))
	{
		ASSERT_FALSE(1);
	}

	Value& categories = doc["categories"];

	ASSERT_TRUE(categories.IsArray());

	ConfigCategories confCategories(result);

	ASSERT_EQ(categories.Size(), confCategories.length());
}

// Get all items of "service" category
TEST(ConfigurationManagerTest, getCategoryItems)
{
	// Before the test start the storage layer with FOGLAMP_DATA=.
	// TCP port will be 8080
	ConfigurationManager *cfgManager = ConfigurationManager::getInstance("127.0.0.1", 8080);
	ConfigCategory category = cfgManager->getCategoryAllItems("service");
	ASSERT_EQ(0, category.getDescription().compare("FogLAMP Service"));
}

// Test check we cannot create a category with both value and default for one item
TEST(ConfigurationManagerTest, addCategoryWithValueAndDefaultForOneItem)
{
	// Before the test start the storage layer with FOGLAMP_DATA=.
	// TCP port will be 8080
	ConfigurationManager *cfgManager = ConfigurationManager::getInstance("127.0.0.1", 8080);
	try
	{
		ConfigCategory category = cfgManager->createCategory("testcategory", "category_description", "{\"info\": {\"description\": \"Test\", \"type\": \"string\", \"default\": \"ONE\", \"value\" : \"ONE\"}, \"detail\": {\"description\": \"detail\", \"type\": \"integer\", \"default\" : \"99\"}}");

		// Test failure
		ASSERT_TRUE(false);
	}
	catch (ConfigValueFoundWithDefault* e)
	{
		// Test success only for found value and default
		ASSERT_FALSE(false);
	}
	catch (...)
	{
		// Test failure
		ASSERT_TRUE(false);
	}
}

// Create a category
TEST(ConfigurationManagerTest, addCategoryWithDefaultValues)
{
	// Before the test start the storage layer with FOGLAMP_DATA=.
	// TCP port will be 8080
	ConfigurationManager *cfgManager = ConfigurationManager::getInstance("127.0.0.1", 8080);
	try
	{
		ConfigCategory category = cfgManager->createCategory("testcategory", "category_description", "{\"item_1\": {\"description\": \"Test\", \"type\": \"string\", \"default\": \"ONE\"}, \"item_2\": {\"description\": \"test_2\", \"type\": \"string\", \"default\": \"____\"}}");

		// Test success
		ASSERT_EQ(2, category.getCount());
		ASSERT_EQ(0, category.getDescription().compare("category_description"));
	}
	catch (...)
	{
		// Test failure
		ASSERT_FALSE(true);
	}
}

// Update a category
TEST(ConfigurationManagerTest, UpdateCategory)
{
	// Before the test start the storage layer with FOGLAMP_DATA=.
	// TCP port will be 8080
	ConfigurationManager *cfgManager = ConfigurationManager::getInstance("127.0.0.1", 8080);
	try
	{
		ConfigCategory category = cfgManager->createCategory("testcategory", "category_description", "{\"item_1\": {\"description\": \"run\", \"type\": \"string\", \"default\": \"TWO\"}, \"item_3\": {\"description\": \"test_3\", \"type\": \"string\", \"default\": \"_3_\"}, \"item_4\": {\"description\": \"the operation\", \"type\": \"integer\", \"default\": \"101\"}}");

		// item_1 gets updated
		// item_2 is removed
		// item_3 is addedd
		// item_4 is addedd

		// Test success
		ASSERT_EQ(3, category.getCount());
		ASSERT_EQ(0, category.getDescription().compare("category_description"));
	}
	catch (...)
	{
		// Test failure
		ASSERT_FALSE(true);
	}
}

// Get a not existing category name
TEST(ConfigurationManagerTest, GetNoExistentCategoryItem)
{
	// Before the test start the storage layer with FOGLAMP_DATA=.
	// TCP port will be 8080
	ConfigurationManager *cfgManager = ConfigurationManager::getInstance("127.0.0.1", 8080);
	try
	{
		// Category item "item_2" doesn't exist
		string item = cfgManager->getCategoryItem("testcategory", "item_2");

		ASSERT_EQ(0, item.compare("{}"));
	
		// Test success
		ASSERT_TRUE(true);
	}
	catch (...)
	{
		// Test failure
		ASSERT_FALSE(true);
	}
}

// Get all details of existing category item
TEST(ConfigurationManagerTest, GetCategoryItem)
{
	// Before the test start the storage layer with FOGLAMP_DATA=.
	// TCP port will be 8080
	ConfigurationManager *cfgManager = ConfigurationManager::getInstance("127.0.0.1", 8080);
	try
	{
		// item_4 exists
		string item = cfgManager->getCategoryItem("testcategory", "item_4");

		// Test success
		ASSERT_TRUE(item.compare("{}") != 0);
	}
	catch (...)
	{
		// Test failure
		ASSERT_FALSE(true);
	}
}

// Get existing value of a category item
TEST(ConfigurationManagerTest, GetCategoryItemValue)
{
	// Before the test start the storage layer with FOGLAMP_DATA=.
	// TCP port will be 8080
	ConfigurationManager *cfgManager = ConfigurationManager::getInstance("127.0.0.1", 8080);
	try
	{
		string item = cfgManager->getCategoryItemValue("testcategory", "item_4");
	
		// Test success
		ASSERT_TRUE(item.compare("") != 0);
		ASSERT_EQ(0, item.compare("101"));
	}
	catch (...)
	{
		// Test failure
		ASSERT_FALSE(true);
	}
}

//Set category item value of an existing item
TEST(ConfigurationManagerTest, SetCategoryItemValue)
{
	// Before the test start the storage layer with FOGLAMP_DATA=.
	// TCP port will be 8080
	ConfigurationManager *cfgManager = ConfigurationManager::getInstance("127.0.0.1", 8080);
	try
	{
		bool item = cfgManager->setCategoryItemValue("testcategory", "item_4", "frog");
	
		// Test success
		ASSERT_TRUE(item);
	}
	catch (...)
	{
		// Test failure
		ASSERT_FALSE(true);
	}
}

//Set category item value of a not existing item
TEST(ConfigurationManagerTest, SetCategoryNotExistingItemValue)
{
	// Before the test start the storage layer with FOGLAMP_DATA=.
	// TCP port will be 8080
	ConfigurationManager *cfgManager = ConfigurationManager::getInstance("127.0.0.1", 8080);
	try
	{
		bool item = cfgManager->setCategoryItemValue("testcategory", "item_xyz", "frog");
	
		// Test failure
		ASSERT_TRUE(false);
	}
	catch (NoSuchItemException& e)
	{
		// Test success
		ASSERT_TRUE(true);
	}
	catch (...)
	{
		// Test failure
		ASSERT_FALSE(true);
	}
}

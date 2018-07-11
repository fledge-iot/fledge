#include <gtest/gtest.h>
#include <config_category.h>
#include <string.h>
#include <string>
#include <rapidjson/document.h>

using namespace std;
using namespace rapidjson;

const char *default_categories = "{\"categories\": ["
	"{\"key\": \"cat1\", \"description\":\"First category\"},"
	"{\"key\": \"cat2\", \"description\":\"Second\"}]}";

const char *default_myCategory = "{\"description\": {"
		"\"type\": \"string\","
		"\"value\": \"The FogLAMP administrative API\","
		"\"default\": \"The FogLAMP administrative API\","
		"\"description\": \"The description of this FogLAMP service\"},"
	"\"name\": {"
		"\"type\": \"string\","
		"\"value\": \"FogLAMP\","
		"\"default\": \"FogLAMP\","
		"\"description\": \"The name of this FogLAMP service\"},"
        "\"complex\": {" \
		"\"type\": \"json\","
		"\"value\": {\"first\" : \"FogLAMP\", \"second\" : \"json\" },"
		"\"default\": {\"first\" : \"FogLAMP\", \"second\" : \"json\" },"
		"\"description\": \"A JSON configuration parameter\"}}";

/**
 * The JSON output from DefaulltCategory::toJSON has "default" values olny
 */
const char *default_json = "{ \"key\" : \"test\", \"description\" : \"Test description\", "
    "\"value\" : {"
	"\"description\" : { "
		"\"description\" : \"The description of this FogLAMP service\", "
		"\"type\" : \"string\", "
		"\"default\" : \"The FogLAMP administrative API\" }, "
	"\"name\" : { "
		"\"description\" : \"The name of this FogLAMP service\", "
		"\"type\" : \"string\", "
		"\"default\" : \"FogLAMP\" }, "
	"\"complex\" : { " 
		"\"description\" : \"A JSON configuration parameter\", "
		"\"type\" : \"json\", "
		"\"default\" : \"{\\\"first\\\":\\\"FogLAMP\\\",\\\"second\\\":\\\"json\\\"}\" }} }";

TEST(DefaultCategoriesTest, Count)
{
	ConfigCategories confCategories(default_categories);
	ASSERT_EQ(2, confCategories.length());
}

TEST(DefaultCategoriesTest, Index)
{
	ConfigCategories confCategories(default_categories);
	const ConfigCategoryDescription *item = confCategories[0];
	ASSERT_EQ(0, item->getName().compare("cat1"));
	ASSERT_EQ(0, item->getDescription().compare("First category"));
}

TEST(DefaultCategoryTest, Construct)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(3, confCategory.getCount());
}

TEST(DefaultCategoryTest, ExistsTest)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(true, confCategory.itemExists("name"));
	ASSERT_EQ(false, confCategory.itemExists("non-existance"));
}

TEST(DefaultCategoryTest, getValue)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(0, confCategory.getValue("name").compare("FogLAMP"));
}

TEST(DefaultCategoryTest, getType)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(0, confCategory.getType("name").compare("string"));
}

TEST(DefaultCategoryTest, getDefault)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(0, confCategory.getDefault("name").compare("FogLAMP"));
}

TEST(DefaultCategoryTest, getDescription)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(0, confCategory.getDescription("name").compare("The name of this FogLAMP service"));
}

TEST(DefaultCategoryTest, isString)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(true, confCategory.isString("name"));
	ASSERT_EQ(false, confCategory.isString("complex"));
}

TEST(DefaultCategoryTest, isJSON)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(false, confCategory.isJSON("name"));
	ASSERT_EQ(true, confCategory.isJSON("complex"));
}

TEST(DefaultCategoryTest, toJSON)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	confCategory.setDescription("Test description");
	// Only "default" value in the output
	ASSERT_EQ(0, confCategory.toJSON().compare(default_json));
}

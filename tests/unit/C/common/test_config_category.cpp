#include <gtest/gtest.h>
#include <config_category.h>
#include <string.h>
#include <string>
#include <rapidjson/document.h>

using namespace std;
using namespace rapidjson;

const char *categories = "{\"categories\": ["
	"{\"key\": \"cat1\", \"description\":\"First category\"},"
	"{\"key\": \"cat2\", \"description\":\"Second\"}]}";

const char *myCategory = "{\"description\": {"
		"\"value\": \"The FogLAMP administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The FogLAMP administrative API\","
		"\"description\": \"The description of this FogLAMP service\"},"
	"\"name\": {"
		"\"value\": \"FogLAMP\","
		"\"type\": \"string\","
		"\"default\": \"FogLAMP\","
		"\"description\": \"The name of this FogLAMP service\"},"
        "\"complex\": {" \
		"\"value\": { \"first\" : \"FogLAMP\", \"second\" : \"json\" },"
		"\"type\": \"json\","
		"\"default\": {\"first\" : \"FogLAMP\", \"second\" : \"json\" },"
		"\"description\": \"A JSON configuration parameter\"}}";

const char *json = "{ \"key\" : \"test\", \"description\" : \"Test description\", "
    "\"value\" : {"
	"\"description\" : { "
		"\"description\" : \"The description of this FogLAMP service\", "
		"\"type\" : \"string\", "
		"\"value\" : \"The FogLAMP administrative API\", "
		"\"default\" : \"The FogLAMP administrative API\" }, "
	"\"name\" : { "
		"\"description\" : \"The name of this FogLAMP service\", "
		"\"type\" : \"string\", "
		"\"value\" : \"FogLAMP\", "
		"\"default\" : \"FogLAMP\" }, "
	"\"complex\" : { " 
		"\"description\" : \"A JSON configuration parameter\", "
		"\"type\" : \"json\", "
		"\"value\" : {\"first\":\"FogLAMP\",\"second\":\"json\"}, "
		"\"default\" : {\"first\":\"FogLAMP\",\"second\":\"json\"} }} }";

const char *allCategories = "[{\"key\": \"cat1\", \"description\" : \"desc1\"}, {\"key\": \"cat2\", \"description\" : \"desc2\"}]";

TEST(CategoriesTest, Count)
{
	ConfigCategories confCategories(categories);
	ASSERT_EQ(2, confCategories.length());
}

TEST(CategoriesTest, Index)
{
	ConfigCategories confCategories(categories);
	const ConfigCategoryDescription *item = confCategories[0];
	ASSERT_EQ(0, item->getName().compare("cat1"));
	ASSERT_EQ(0, item->getDescription().compare("First category"));
}

TEST(CategoriesTest, addElements)
{
	ConfigCategories categories;
	ConfigCategoryDescription *one = new ConfigCategoryDescription(string("cat1"), string("desc1"));
	ConfigCategoryDescription *two = new ConfigCategoryDescription(string("cat2"), string("desc2"));
	categories.addCategoryDescription(one);
	categories.addCategoryDescription(two);
	ASSERT_EQ(2, categories.length());
}

TEST(CategoriesTest, toJSON)
{
	ConfigCategories categories;
	ConfigCategoryDescription *one = new ConfigCategoryDescription(string("cat1"), string("desc1"));
	ConfigCategoryDescription *two = new ConfigCategoryDescription(string("cat2"), string("desc2"));
	categories.addCategoryDescription(one);
	categories.addCategoryDescription(two);
	string result =  categories.toJSON();
	ASSERT_EQ(2, categories.length());
	ASSERT_EQ(0, result.compare(allCategories));
}

TEST(CategoryTest, Construct)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(3, confCategory.getCount());
}

TEST(CategoryTest, ExistsTest)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(true, confCategory.itemExists("name"));
	ASSERT_EQ(false, confCategory.itemExists("non-existance"));
}

TEST(CategoryTest, getValue)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(0, confCategory.getValue("name").compare("FogLAMP"));
}

TEST(CategoryTest, getType)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(0, confCategory.getType("name").compare("string"));
}

TEST(CategoryTest, getDefault)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(0, confCategory.getDefault("name").compare("FogLAMP"));
}

TEST(CategoryTest, getDescription)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(0, confCategory.getDescription("name").compare("The name of this FogLAMP service"));
}

TEST(CategoryTest, isString)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(true, confCategory.isString("name"));
	ASSERT_EQ(false, confCategory.isString("complex"));
}

TEST(CategoryTest, isJSON)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(false, confCategory.isJSON("name"));
	ASSERT_EQ(true, confCategory.isJSON("complex"));
}

TEST(CategoryTest, toJSON)
{
	ConfigCategory confCategory("test", myCategory);
	confCategory.setDescription("Test description");
	ASSERT_EQ(0, confCategory.toJSON().compare(json));
}

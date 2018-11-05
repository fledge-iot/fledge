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

const char *default_myCategory_number_and_boolean_items =  "{\"factor\": {"
		"\"value\": \"101\","
		"\"type\": \"integer\","
		"\"default\": 100,"
		"\"description\": \"The factor value\"}, "
	"\"enable\" : {"
	"\"description\": \"Switch enabled\", "
	"\"default\" : \"false\", "
	"\"value\" : true, "
	"\"type\" : \"boolean\"}}";

// NOTE: toJSON() methods return escaped content for default properties 
const char *default_json_boolean_number = "{ \"key\" : \"test\", \"description\" : \"Test description\", "
				"\"value\" : "
		"{\"factor\" : { \"description\" : \"The factor value\", \"type\" : \"integer\", "
			"\"default\" : \"100\" }, "
		"\"enable\" : { \"description\" : \"Switch enabled\", \"type\" : \"boolean\", "
			"\"default\" : \"false\" }} }";

const char *default_myCategory_JSON_type_with_escaped_default = "{ "
        "\"filter\": { "
                "\"type\": \"JSON\", "
                "\"description\": \"filter\", "
                "\"default\": \"{\\\"pipeline\\\":[\\\"scale\\\",\\\"exceptional\\\"]}\", "
                "\"value\": \"{}\" } }";

// NOTE: toJSON() methods return escaped content for default properties 
const char *default_json_type_JSON = "{ \"key\" : \"test\", \"description\" : \"Test description\", "
                "\"value\" : {\"filter\" : { \"description\" : \"filter\", \"type\" : \"JSON\", "
                "\"default\" : \"{\\\"pipeline\\\":[\\\"scale\\\",\\\"exceptional\\\"]}\" }} }";

// default has invalid (escaped) JSON object value here: a \\\" is missing for pipeline
const char *default_myCategory_JSON_type_without_escaped_default = "{ "
        "\"filter\": { "
                "\"type\": \"JSON\", "
                "\"description\": \"filter\", "
                "\"default\": \"{\"pipeline\\\" : \\\"scale\\\", \\\"exceptional\\\"]}\", "
                "\"value\": \"{}\" } }";

// This is the output pf getValue or getDefault and the contend is unescaped
const char *default_json_array_item = "{\"pipeline\":[\"scale\",\"exceptional\"]}";

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

TEST(DefaultCategoryTest, default_bool_and_number_ok)
{       
	DefaultConfigCategory confCategory("test",
					   default_myCategory_number_and_boolean_items);
	confCategory.setDescription("Test description");

	//confCategory.checkDefaultValuesOnly();
	ASSERT_EQ(true, confCategory.isBool("enable"));
	ASSERT_EQ(true, confCategory.isNumber("factor"));
	ASSERT_EQ(0, confCategory.getValue("factor").compare("101"));
	ASSERT_EQ(0, confCategory.getDefault("factor").compare("100"));
	ASSERT_EQ(0, confCategory.toJSON().compare(default_json_boolean_number));
}

TEST(CategoryTest, default_handle_type_JSON_ok)
{
        DefaultConfigCategory confCategory("test",
					   default_myCategory_JSON_type_with_escaped_default);
        confCategory.setDescription("Test description");
        ASSERT_EQ(true, confCategory.isJSON("filter"));

        Document arrayItem;
        arrayItem.Parse(confCategory.getDefault("filter").c_str());
        const Value& arrayValue = arrayItem["pipeline"];

        ASSERT_TRUE(arrayValue.IsArray());
        ASSERT_TRUE(arrayValue.Size() == 2);
        ASSERT_EQ(0, confCategory.getDefault("filter").compare(default_json_array_item));
        ASSERT_EQ(0, confCategory.toJSON().compare(default_json_type_JSON));
}

TEST(CategoryTest, default_handle_type_JSON_fail)
{
        try
        {
                DefaultConfigCategory confCategory("test",
						   default_myCategory_JSON_type_without_escaped_default);
                confCategory.setDescription("Test description");

                // test fails here!
                ASSERT_TRUE(false);
        }
        catch (...)
        {
                // Test ok; exception found
                ASSERT_TRUE(true);
        }
}

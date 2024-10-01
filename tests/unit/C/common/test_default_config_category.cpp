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

const char *default_categories_quoted = "{\"categories\": ["
	"{\"key\": \"cat\\\"1\\\"\", \"description\":\"The \\\"First\\\" category\"},"
	"{\"key\": \"cat\\\"2\\\"\", \"description\":\"The \\\"Second\\\" category\"}]}";

const char *default_myCategory = "{\"description\": {"
		"\"type\": \"string\","
		"\"value\": \"The Fledge administrative API\","
		"\"default\": \"The Fledge administrative API\","
		"\"description\": \"The description of this Fledge service\"},"
	"\"name\": {"
		"\"type\": \"string\","
		"\"value\": \"Fledge\","
		"\"default\": \"Fledge\","
		"\"description\": \"The name of this Fledge service\"},"
        "\"complex\": {" \
		"\"type\": \"json\","
		"\"value\": {\"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"default\": {\"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"description\": \"A JSON configuration parameter\"}}";

const char *default_myCategory_quoted = "{\"description\": {"
		"\"type\": \"string\","
		"\"value\": \"The \\\"Fledge\\\" administrative API\","
		"\"default\": \"The \\\"Fledge\\\" administrative API\","
		"\"description\": \"The description of this \\\"Fledge\\\" service\"},"
	"\"name\": {"
		"\"type\": \"string\","
		"\"value\": \"\\\"Fledge\\\"\","
		"\"default\": \"\\\"Fledge\\\"\","
		"\"description\": \"The name of this \\\"Fledge\\\" service\"},"
        "\"complex\": {" \
		"\"type\": \"json\","
		"\"value\": {\"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"default\": {\"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"description\": \"A JSON configuration parameter\"}}";

const char *default_myCategory_quotedSpecial = R"DQS({ "description": { "type": "string", "value": "The \"Fledge\" administra\tive API", "default": "The \"Fledge\" admini\\strative API", "description": "The description of this \"Fledge\" service"}, "name": { "type": "string", "value": "\"Fledge\"", "default": "\"Fledge\"", "description": "The name of this \"Fledge\" service"}, "complex": { "type": "json", "value": {"first" : "Fledge", "second" : "json" }, "default": {"first" : "Fledge", "second" : "json" }, "description": "A JSON configuration parameter"}})DQS";

/**
 * The JSON output from DefaulltCategory::toJSON has "default" values olny
 */
const char *default_json = "{ \"key\" : \"test\", \"description\" : \"Test description\", "
    "\"value\" : {"
	"\"description\" : { "
		"\"description\" : \"The description of this Fledge service\", "
		"\"type\" : \"string\", "
		"\"default\" : \"The Fledge administrative API\" }, "
	"\"name\" : { "
		"\"description\" : \"The name of this Fledge service\", "
		"\"type\" : \"string\", "
		"\"default\" : \"Fledge\" }, "
	"\"complex\" : { " 
		"\"description\" : \"A JSON configuration parameter\", "
		"\"type\" : \"json\", "
		"\"default\" : \"{\\\"first\\\":\\\"Fledge\\\",\\\"second\\\":\\\"json\\\"}\" }} }";

const char *default_json_quoted = "{ \"key\" : \"test \\\"a\\\"\", \"description\" : \"Test \\\"description\\\"\", "
    "\"value\" : {"
	"\"description\" : { "
		"\"description\" : \"The description of this \\\"Fledge\\\" service\", "
		"\"type\" : \"string\", "
		"\"default\" : \"The \\\"Fledge\\\" administrative API\" }, "
	"\"name\" : { "
		"\"description\" : \"The name of this \\\"Fledge\\\" service\", "
		"\"type\" : \"string\", "
		"\"default\" : \"\\\"Fledge\\\"\" }, "
	"\"complex\" : { " 
		"\"description\" : \"A JSON configuration parameter\", "
		"\"type\" : \"json\", "
		"\"default\" : \"{\\\"first\\\":\\\"Fledge\\\",\\\"second\\\":\\\"json\\\"}\" }} }";

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

const char *myDefCategoryRemoveItems = "{" \
			"\"plugin\" : {"\
				"\"description\" : \"Random C south plugin\", "\
				"\"type\" : \"string\", "\
				"\"default\" : \"Random_2\" "\
			"}, "\
			"\"asset\" : {"\
				"\"description\" : \"Asset name\", " \
				"\"type\" : \"category\", "\
				"\"default\" : {"\
					"\"bias\" : {"\
						"\"description\" : \"Bias offset\", "\
						"\"type\" : \"float\", "\
						"\"default\" : \"2\" "\
					"} "\
				"} "\
			"} "\
		"}";


const char *default_json_quotedSpecial = R"SDQ({ "key" : "test \"a\"", "description" : "Test \"description\"", "value" : {"description" : { "description" : "The description of this \"Fledge\" service", "type" : "string", "default" : "The \"Fledge\" admini\\strative API" }, "name" : { "description" : "The name of this \"Fledge\" service", "type" : "string", "default" : "\"Fledge\"" }, "complex" : { "description" : "A JSON configuration parameter", "type" : "json", "default" : "{\"first\":\"Fledge\",\"second\":\"json\"}" }} })SDQ";

TEST(DefaultCategoriesTest, Count)
{
	ConfigCategories confCategories(default_categories);
	ASSERT_EQ(2, confCategories.length());
}

TEST(DefaultCategoriesTestQuoted, CountQuoted)
{
	ConfigCategories confCategories(default_categories_quoted);
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

TEST(DefaultCategoryTestQuoted, ConstructQuoted)
{
	DefaultConfigCategory confCategory("test", default_myCategory_quoted);
	ASSERT_EQ(3, confCategory.getCount());
}

TEST(DefaultCategoryTest, ExistsTest)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(true, confCategory.itemExists("name"));
	ASSERT_EQ(false, confCategory.itemExists("non-existance"));
}

TEST(DefaultCategoryTestQuoted, ExistsTestQuoted)
{
	DefaultConfigCategory confCategory("test", default_myCategory_quoted);
	ASSERT_EQ(true, confCategory.itemExists("name"));
	ASSERT_EQ(false, confCategory.itemExists("non-existance"));
}

TEST(DefaultCategoryTest, getValue)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(0, confCategory.getValue("name").compare("Fledge"));
}

TEST(DefaultCategoryTestQuoted, getValueQuoted)
{
	DefaultConfigCategory confCategory("test", default_myCategory_quoted);
	ASSERT_EQ(0, confCategory.getValue("name").compare("\"Fledge\""));
}

TEST(DefaultCategoryTest, getType)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(0, confCategory.getType("name").compare("string"));
}

TEST(DefaultCategoryTest, getDefault)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(0, confCategory.getDefault("name").compare("Fledge"));
}

TEST(DefaultCategoryTestQuoted, getDefaultQuoted)
{
	DefaultConfigCategory confCategory("test", default_myCategory_quoted);
	ASSERT_EQ(0, confCategory.getDefault("name").compare("\"Fledge\""));
}

TEST(DefaultCategoryTest, getDescription)
{
	DefaultConfigCategory confCategory("test", default_myCategory);
	ASSERT_EQ(0, confCategory.getDescription("name").compare("The name of this Fledge service"));
}

TEST(DefaultCategoryTestQuoted, getDescriptionQuoted)
{
	DefaultConfigCategory confCategory("test", default_myCategory_quoted);
	ASSERT_EQ(0, confCategory.getDescription("name").compare("The name of this \"Fledge\" service"));
}

TEST(DefaultCategoryTestQuoted, isStringQuoted)
{
	DefaultConfigCategory confCategory("test", default_myCategory_quoted);
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

TEST(DefaultCategoryTestQuoted, toJSONQuoted)
{
	DefaultConfigCategory confCategory("test \"a\"", default_myCategory_quoted);
	confCategory.setDescription("Test \"description\"");
	// Only "default" value in the output
	ASSERT_EQ(0, confCategory.toJSON().compare(default_json_quoted));
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
	catch (exception *e)
	{
		delete e;
		// Test ok; exception found
		ASSERT_TRUE(true);
	}
        catch (...)
        {
                // Test ok; exception found
                ASSERT_TRUE(true);
        }
}


TEST(DefaultCategoryTest, removeItemsType)
{
	DefaultConfigCategory defCategory("test", myDefCategoryRemoveItems);
	ASSERT_EQ(2, defCategory.getCount());

	defCategory.removeItemsType(ConfigCategory::ItemType::CategoryType);
	ASSERT_EQ(1, defCategory.getCount());

}

/**
 * Test special quoted chars
 */

TEST(DefaultCategoryTestQuoted, toJSONQuotedSpecial)
{
	DefaultConfigCategory confCategory("test \"a\"", default_myCategory_quotedSpecial);
	confCategory.setDescription("Test \"description\"");

	// Only "default" value in the output
	ASSERT_EQ(0, confCategory.toJSON().compare(default_json_quotedSpecial));
}

// Default config category with \n in default JSON
string jsonLF = R"({"plugin": {"description": "Sinusoid Poll Plugin which implements sine wave with data points", "type": "string", "default": "sinusoid", "readonly": "true"}, "assetName": {"description": "Name of Asset", "type": "string", "default": "sinusoid", "displayName": "Asset name", "mandatory": "true"}, "writemap": {"description": "Map of tags", "displayName": "Tags to write", "type": "JSON", "default": "{\n  \"tags\": [\n    {\n      \"name\": \"PLCTAG\",\n      \"type\": \"UINT32\",\n      \"program\": \"\"\n    }\n  ]\n}"}})";
string jsonClear = R"({  "tags": [    {      "name": "PLCTAG",      "type": "UINT32",      "program": ""    }  ]})";

TEST(DefaultCategoryTestLF, toJSONWithoutLF)
{
	DefaultConfigCategory confCategory("testLF", jsonLF);
	confCategory.setDescription("Test description");

	// Only "default" value in the output
	ASSERT_EQ(0, confCategory.getDefault("writemap").compare(jsonClear));
}

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

const char *myCategoryDisplayName = "{\"description\": {"
		"\"value\": \"The FogLAMP administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The FogLAMP administrative API\","
		"\"description\": \"The description of this FogLAMP service\"},"
	"\"name\": {"
		"\"value\": \"FogLAMP\","
		"\"displayName\" : \"My FogLAMP\","
		"\"type\": \"string\","
		"\"default\": \"FogLAMP\","
		"\"description\": \"The name of this FogLAMP service\"},"
        "\"complex\": {" \
		"\"value\": { \"first\" : \"FogLAMP\", \"second\" : \"json\" },"
		"\"type\": \"json\","
		"\"default\": {\"first\" : \"FogLAMP\", \"second\" : \"json\" },"
		"\"description\": \"A JSON configuration parameter\"}}";

const char *myCategoryEnum = "{\"description\": {"
		"\"value\": \"The FogLAMP administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The FogLAMP administrative API\","
		"\"description\": \"The description of this FogLAMP service\"},"
	"\"name\": {"
		"\"value\": \"FogLAMP\","
		"\"type\": \"string\","
		"\"default\": \"FogLAMP\","
		"\"description\": \"The name of this FogLAMP service\"},"
        "\"enum\": {" \
		"\"value\": \"first\","
		"\"type\": \"enumeration\","
		"\"default\": \"first\","
		"\"options\": [\"first\", \"second\", \"third\"],"
		"\"description\": \"An enumeration configuration parameter\"}}";

const char *enum_JSON = "{ \"key\" : \"test\", \"description\" : \"\", \"value\" : {\"description\" : { \"description\" : \"The description of this FogLAMP service\", \"type\" : \"string\", \"value\" : \"The FogLAMP administrative API\", \"default\" : \"The FogLAMP administrative API\" }, \"name\" : { \"description\" : \"The name of this FogLAMP service\", \"type\" : \"string\", \"value\" : \"FogLAMP\", \"default\" : \"FogLAMP\" }, \"enum\" : { \"description\" : \"An enumeration configuration parameter\", \"type\" : \"enumeration\", \"options\" : [ \"first\",\"second\",\"third\"],\"value\" : \"first\", \"default\" : \"first\" }} }";

const char *myCategory_JSON_type_with_escaped_default = "{ "
	"\"filter\": { "
		"\"type\": \"JSON\", "
		"\"description\": \"filter\", "
		"\"default\": \"{\\\"pipeline\\\":[\\\"scale\\\",\\\"exceptional\\\"]}\", "
		"\"value\": \"{}\" } }";

const char *myCategoryMinMax = "{\"description\": {"
		"\"value\": \"The FogLAMP administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The FogLAMP administrative API\","
		"\"description\": \"The description of this FogLAMP service\"},"
	"\"range\": {"
		"\"value\": \"1\","
		"\"type\": \"integer\","
		"\"default\": \"1\","
		"\"minimum\": \"1\","
		"\"maximum\": \"10\","
		"\"description\": \"A constrained value\"},"
        "\"complex\": {" \
		"\"value\": { \"first\" : \"FogLAMP\", \"second\" : \"json\" },"
		"\"type\": \"json\","
		"\"default\": {\"first\" : \"FogLAMP\", \"second\" : \"json\" },"
		"\"description\": \"A JSON configuration parameter\"}}";

const char *myCategoryRemoveItems = "{" \
			"\"plugin\" : {"\
				"\"description\" : \"Random C south plugin\", "\
				"\"type\" : \"string\", "\
				"\"default\" : \"Random_2\", "\
				"\"value\" : \"Random_2\" "\
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
				"}, "\
				"\"value\" : {"\
					"\"bias\" : {"\
						"\"description\" : \"Bias offset\", "\
						"\"type\" : \"float\", "\
						"\"default\" : \"2\" "\
					"} "\
				"} "\
			"} "\
		"}";


// default has invalid (escaped) JSON object value here: a \\\" is missing for pipeline
const char *myCategory_JSON_type_without_escaped_default = "{ "
	"\"filter\": { "
		"\"type\": \"JSON\", "
		"\"description\": \"filter\", "
		"\"default\": \"{\"pipeline\\\" : \\\"scale\\\", \\\"exceptional\\\"]}\", "
		"\"value\": \"{}\" } }";

const char *myCategoryDeprecated = "{\"description\": {"
		"\"value\": \"The FogLAMP administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The FogLAMP administrative API\","
		"\"description\": \"The description of this FogLAMP service\"},"
	"\"name\": {"
		"\"value\": \"FogLAMP\","
		"\"type\": \"string\","
		"\"default\": \"FogLAMP\","
		"\"description\": \"The name of this FogLAMP service\"},"
        "\"location\": {" \
		"\"value\": \"remote\","
		"\"type\": \"string\","
		"\"default\": \"local\", "
		"\"deprecated\": \"true\", "
		"\"description\": \"A deprecated configuration parameter\"}}";

const char *json_array_item = "{\"pipeline\":[\"scale\",\"exceptional\"]}";

const char *myCategory_number_and_boolean_items =  "{\"factor\": {"
		"\"value\": \"112\","
		"\"type\": \"integer\","
		"\"default\": 101,"
		"\"description\": \"The factor value\"}, "
	"\"enable\" : {"
	"\"description\": \"Switch enabled\", "
	"\"default\" : \"false\", "
	"\"value\" : true, "
	"\"type\" : \"boolean\"}}";

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

const char *json_type_JSON = "{ \"key\" : \"test\", \"description\" : \"Test description\", "
		"\"value\" : {\"filter\" : { \"description\" : \"filter\", \"type\" : \"JSON\", "
		"\"value\" : {}, \"default\" : {\"pipeline\":[\"scale\",\"exceptional\"]} }} }";

const char *json_boolean_number = "{ \"key\" : \"test\", \"description\" : \"Test description\", "
				"\"value\" : "
		"{\"factor\" : { \"description\" : \"The factor value\", \"type\" : \"integer\", "
			"\"value\" : 112, \"default\" : 101 }, "
		"\"enable\" : { \"description\" : \"Switch enabled\", \"type\" : \"boolean\", "
			"\"value\" : \"true\", \"default\" : \"false\" }} }";

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

TEST(CategoryTest, bool_and_number_ok)
{
	ConfigCategory confCategory("test", myCategory_number_and_boolean_items);
	confCategory.setDescription("Test description");
	ASSERT_EQ(true, confCategory.isBool("enable"));
	ASSERT_EQ(true, confCategory.isNumber("factor"));
	ASSERT_EQ(0, confCategory.toJSON().compare(json_boolean_number));
	ASSERT_EQ(0, confCategory.getValue("factor").compare("112"));
}

TEST(CategoryTest, handle_type_JSON_ok)
{
	ConfigCategory confCategory("test", myCategory_JSON_type_with_escaped_default);
	confCategory.setDescription("Test description");
	ASSERT_EQ(true, confCategory.isJSON("filter"));

	Document arrayItem;
	arrayItem.Parse(confCategory.getDefault("filter").c_str());
	const Value& arrayValue = arrayItem["pipeline"];

	ASSERT_TRUE(arrayValue.IsArray());
	ASSERT_TRUE(arrayValue.Size() == 2);
	ASSERT_EQ(0, confCategory.getDefault("filter").compare(json_array_item));
	ASSERT_EQ(0, confCategory.toJSON().compare(json_type_JSON));
}

TEST(CategoryTest, handle_type_JSON_fail)
{
	try
	{
		ConfigCategory confCategory("test", myCategory_JSON_type_without_escaped_default);
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

TEST(CategoryTest, enumerationTest)
{
	ConfigCategory confCategory("test", myCategoryEnum);
	ASSERT_EQ(true, confCategory.isEnumeration("enum"));
	std::vector<std::string> options = confCategory.getOptions("enum");
	ASSERT_EQ(3, options.size());
}

TEST(CategoryTest, enumerationJSONTest)
{
	ConfigCategory confCategory("test", myCategoryEnum);
	ASSERT_EQ(true, confCategory.isEnumeration("enum"));
	std::vector<std::string> options = confCategory.getOptions("enum");
	ASSERT_EQ(3, options.size());
	ASSERT_EQ(0, confCategory.toJSON().compare(enum_JSON));
}

TEST(CategoryTest, displayName)
{
	ConfigCategory confCategory("test", myCategoryDisplayName);
	ASSERT_EQ("My FogLAMP", confCategory.getDisplayName("name"));
}

TEST(CategoryTest, deprecated)
{
	ConfigCategory confCategory("test", myCategoryDeprecated);
	ASSERT_EQ(false, confCategory.isDeprecated("name"));
	ASSERT_EQ(true, confCategory.isDeprecated("location"));
}

TEST(CategoryTest, minMax)
{
	ConfigCategory confCategory("test", myCategoryMinMax);
	ASSERT_EQ("1", confCategory.getMinimum("range"));
	ASSERT_EQ("10", confCategory.getMaximum("range"));
}

TEST(CategoryTest, removeItems)
{
	ConfigCategory confCategory("test", myCategoryRemoveItems);
	ASSERT_EQ(2, confCategory.getCount());

	confCategory.removeItems();
	ASSERT_EQ(0, confCategory.getCount());
}

TEST(CategoryTest, removeItemsType)
{
	ConfigCategory conf2Category("test", myCategoryRemoveItems);
	ASSERT_EQ(2, conf2Category.getCount());

	conf2Category.removeItemsType(ConfigCategory::ItemType::CategoryType);
	ASSERT_EQ(1, conf2Category.getCount());

}


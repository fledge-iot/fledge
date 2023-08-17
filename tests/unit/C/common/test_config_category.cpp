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

const char *categories_quoted = "{\"categories\": ["
	"{\"key\": \"cat \\\"1\\\"\", \"description\":\"First \\\"category\\\"\"},"
	"{\"key\": \"cat \\\"2\\\"\", \"description\":\"Second\"}]}";

const char *myCategory = "{\"description\": {"
		"\"value\": \"The Fledge administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The Fledge administrative API\","
		"\"description\": \"The description of this Fledge service\"},"
	"\"name\": {"
		"\"value\": \"Fledge\","
		"\"type\": \"string\","
		"\"default\": \"Fledge\","
		"\"description\": \"The name of this Fledge service\"},"
        "\"complex\": {" \
		"\"value\": { \"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"type\": \"json\","
		"\"default\": {\"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"description\": \"A JSON configuration parameter\"}}";

const char *myCategory_quoted = "{\"description\": {"
		"\"value\": \"The \\\"Fledge\\\" administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The \\\"Fledge\\\" administrative API\","
		"\"description\": \"The description of this \\\"Fledge\\\" service\"},"
	"\"name\": {"
		"\"value\": \"\\\"Fledge\\\"\","
		"\"type\": \"string\","
		"\"default\": \"\\\"Fledge\\\"\","
		"\"description\": \"The name of this \\\"Fledge\\\" service\"},"
        "\"complex\": {" \
		"\"value\": { \"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"type\": \"json\","
		"\"default\": {\"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"description\": \"A JSON configuration parameter\"}}";

const char *myCategory_quotedSpecial = R"QQ({"description": { "value": "The \"Fledge\" admini\\strative API", "type": "string", "default": "The \"Fledge\" administra\tive API", "description": "The description of this \"Fledge\" service"}, "name": { "value": "\"Fledge\"", "type": "string", "default": "\"Fledge\"", "description": "The name of this \"Fledge\" service"}, "complex": { "value": { "first" : "Fledge", "second" : "json" }, "type": "json", "default": {"first" : "Fledge", "second" : "json" }, "description": "A JSON configuration parameter"} })QQ";

const char *myCategoryDisplayName = "{\"description\": {"
		"\"value\": \"The Fledge administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The Fledge administrative API\","
		"\"description\": \"The description of this Fledge service\"},"
	"\"name\": {"
		"\"value\": \"Fledge\","
		"\"displayName\" : \"My Fledge\","
		"\"type\": \"string\","
		"\"default\": \"Fledge\","
		"\"description\": \"The name of this Fledge service\"},"
        "\"complex\": {" \
		"\"value\": { \"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"type\": \"json\","
		"\"default\": {\"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"description\": \"A JSON configuration parameter\"}}";

const char *myCategoryEnum = "{\"description\": {"
		"\"value\": \"The Fledge administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The Fledge administrative API\","
		"\"description\": \"The description of this Fledge service\"},"
	"\"name\": {"
		"\"value\": \"Fledge\","
		"\"type\": \"string\","
		"\"default\": \"Fledge\","
		"\"description\": \"The name of this Fledge service\"},"
        "\"enum\": {" \
		"\"value\": \"first\","
		"\"type\": \"enumeration\","
		"\"default\": \"first\","
		"\"options\": [\"first\",\"second\",\"third\"], "
		"\"description\": \"An enumeration configuration parameter\"}}";

const char *enum_JSON = "{ \"key\" : \"test\", \"description\" : \"\", \"value\" : {\"description\" : { \"description\" : \"The description of this Fledge service\", \"type\" : \"string\", \"value\" : \"The Fledge administrative API\", \"default\" : \"The Fledge administrative API\" }, \"name\" : { \"description\" : \"The name of this Fledge service\", \"type\" : \"string\", \"value\" : \"Fledge\", \"default\" : \"Fledge\" }, \"enum\" : { \"description\" : \"An enumeration configuration parameter\", \"type\" : \"enumeration\", \"options\" : [ \"first\",\"second\",\"third\"], \"value\" : \"first\", \"default\" : \"first\" }} }";

const char *myCategory_JSON_type_with_escaped_default = "{ "
	"\"filter\": { "
		"\"type\": \"JSON\", "
		"\"description\": \"filter\", "
		"\"default\": \"{\\\"pipeline\\\":[\\\"scale\\\",\\\"exceptional\\\"]}\", "
		"\"value\": \"{}\" } }";

const char *myCategoryMinMax = "{\"description\": {"
		"\"value\": \"The Fledge administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The Fledge administrative API\","
		"\"description\": \"The description of this Fledge service\"},"
	"\"range\": {"
		"\"value\": \"1\","
		"\"type\": \"integer\","
		"\"default\": \"1\","
		"\"minimum\": \"1\","
		"\"maximum\": \"10\","
		"\"description\": \"A constrained value\"},"
        "\"complex\": {" \
		"\"value\": { \"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"type\": \"json\","
		"\"default\": {\"first\" : \"Fledge\", \"second\" : \"json\" },"
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


const char *myCategoryScript = "{\"config\": {\"displayName\": \"Configuration\", \"order\": \"1\", "
					"\"default\": \"{}\", \"value\": \"{\\\"d\\\":76}\", "
					"\"type\": \"JSON\", \"description\": \"Python 2.7 filter configuration.\"}, "
				"\"plugin\": {\"readonly\": \"true\", \"default\": \"python27\", "
					"\"type\": \"string\", \"value\": \"python27\", "
					"\"description\": \"Python 2.7 filter plugin\"}, "
				"\"enable\": {\"displayName\": \"Enabled\", \"default\": \"false\", "
					"\"type\": \"boolean\", \"value\": \"true\", "
					"\"description\": \"A switch that can be used to enable or disable execution of the Python 2.7 filter.\"}, "
				"\"script\": {\"displayName\": \"Python Script\", \"order\": \"2\", "
					"\"default\": \"\", "
					"\"value\": \"\\\"\\\"\\\"\\nFledge filtering for readings data\\\"\\\"\\\"\\n"
						"def set_filter_config(configuration):\\n"
						"    print configuration\\n"
						"    global filter_config\\n"
						"    filter_config = json.loads(configuration['config'])\\n\\n"
						"    return True\\n\\n\", "
					"\"file\": \"/home/ubuntu/source/develop/Fledge/data/scripts/pumpa_powerfilter_script_file27.py\", "
					"\"type\": \"script\", "
					"\"description\": \"Python 2.7 module to load.\" } }";

// default has invalid (escaped) JSON object value here: a \\\" is missing for pipeline
const char *myCategory_JSON_type_without_escaped_default = "{ "
	"\"filter\": { "
		"\"type\": \"JSON\", "
		"\"description\": \"filter\", "
		"\"default\": \"{\"pipeline\\\" : \\\"scale\\\", \\\"exceptional\\\"]}\", "
		"\"value\": \"{}\" } }";

const char *myCategoryDeprecated = "{\"description\": {"
		"\"value\": \"The Fledge administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The Fledge administrative API\","
		"\"description\": \"The description of this Fledge service\"},"
	"\"name\": {"
		"\"value\": \"Fledge\","
		"\"type\": \"string\","
		"\"default\": \"Fledge\","
		"\"description\": \"The name of this Fledge service\"},"
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


const char *myCategory_to_json_parameters = "{"\
		"\"memoryBufferSize\": {"
			"\"description\": \"Number of elements of blockSize size to be buffered in memory\","
			"\"type\": \"integer\", "
			"\"default\": \"10\", "
			"\"order\": \"12\" ,"
			"\"readonly\": \"false\" "
		"} "
	"}";

const char *json = "{ \"key\" : \"test\", \"description\" : \"Test description\", "
    "\"value\" : {"
	"\"description\" : { "
		"\"description\" : \"The description of this Fledge service\", "
		"\"type\" : \"string\", "
		"\"value\" : \"The Fledge administrative API\", "
		"\"default\" : \"The Fledge administrative API\" }, "
	"\"name\" : { "
		"\"description\" : \"The name of this Fledge service\", "
		"\"type\" : \"string\", "
		"\"value\" : \"Fledge\", "
		"\"default\" : \"Fledge\" }, "
	"\"complex\" : { " 
		"\"description\" : \"A JSON configuration parameter\", "
		"\"type\" : \"json\", "
		"\"value\" : {\"first\":\"Fledge\",\"second\":\"json\"}, "
		"\"default\" : {\"first\":\"Fledge\",\"second\":\"json\"} }} }";

const char *json_quoted = "{ \"key\" : \"test \\\"a\\\"\", \"description\" : \"Test \\\"description\\\"\", "
    "\"value\" : {"
	"\"description\" : { "
		"\"description\" : \"The description of this \\\"Fledge\\\" service\", "
		"\"type\" : \"string\", "
		"\"value\" : \"The \\\"Fledge\\\" administrative API\", "
		"\"default\" : \"The \\\"Fledge\\\" administrative API\" }, "
	"\"name\" : { "
		"\"description\" : \"The name of this \\\"Fledge\\\" service\", "
		"\"type\" : \"string\", "
		"\"value\" : \"\\\"Fledge\\\"\", "
		"\"default\" : \"\\\"Fledge\\\"\" }, "
	"\"complex\" : { " 
		"\"description\" : \"A JSON configuration parameter\", "
		"\"type\" : \"json\", "
		"\"value\" : {\"first\":\"Fledge\",\"second\":\"json\"}, "
		"\"default\" : {\"first\":\"Fledge\",\"second\":\"json\"} }} }";

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
const char *allCategories_quoted = "[{\"key\": \"cat\\\"1\\\"\", \"description\" : \"desc\\\"1\\\"\"}, "
				   "{\"key\": \"cat\\\"2\\\"\", \"description\" : \"desc\\\"2\\\"\"}]";

const char *myCategoryEnumFull = "{\"description\": {"
		"\"value\": \"The Fledge administrative API\","
		"\"type\": \"string\", \"order\" : \"1\", "
		"\"default\": \"The Fledge administrative API\", "
		"\"description\": \"The description of this Fledge service\"}, "
	"\"name\": {"
		"\"value\": \"Fledge\", \"readonly\" : \"false\", "
		"\"type\": \"string\", \"order\" : \"2\", "
		"\"default\": \"Fledge\", \"displayName\" : \"Fledge service\", "
		"\"description\": \"The name of this Fledge service\"}, "
	"\"range\": {"
		"\"value\": \"1\","
		"\"type\": \"integer\","
		"\"default\": \"1\","
		"\"minimum\": \"1\", "
		"\"maximum\": \"10\", \"order\" : \"4\",  \"displayName\" : \"Fledge range parameter\", "
		"\"description\": \"A constrained value\"},"
        "\"enum\": {" \
		"\"value\": \"first\","
		"\"type\": \"enumeration\", \"order\" : \"3\", "
		"\"default\": \"first\", \"displayName\" : \"Fledge configuration parameter\", "
		"\"options\": [\"first\",\"second\",\"third\"], "
		"\"description\": \"An enumeration configuration parameter\"}}";

const char* bigCategory =
		"{\"OMFMaxRetry\": { " \
			"\"type\": \"integer\", \"displayName\": \"Maximum Retry\", " \
			"\"value\": \"3\", \"default\": \"3\", " \
			"\"description\": \"Max number of retries\", " \
			"\"order\": \"10\"}, "
		"\"compression\": { " \
			"\"type\": \"boolean\", \"displayName\": \"Compression\", " \
			"\"value\": \"false\", \"default\": \"true\", " \
			"\"description\": \"Compress data before sending\", " \
			"\"order\": \"16\"}, " \
			"\"enable\": {\"type\": \"boolean\", \"description\": " \
				"\"A switch that can be used to enable or disable execution\", " \
			"\"default\": \"true\", \"value\": \"true\", \"readonly\": \"true\"}, " \
		"\"plugin\": { " \
			"\"type\": \"string\", " \
			"\"description\": \"PI Server North C Plugin\", " \
			"\"default\": \"OMF\", " \
			"\"value\": \"OMF\", \"readonly\": \"true\"}, " \
		"\"source\": { " \
			"\"type\": \"enumeration\", " \
			"\"options\": [\"readings\", \"statistics\"], " \
			"\"displayName\": \"Data Source\", " \
			"\"value\": \"readings\", " \
			"\"default\": \"readings\", " \
			"\"description\": \"Defines\"} " \
		"}";

const char *optionals = 
	"{\"item1\" : { "\
			"\"type\": \"integer\", \"displayName\": \"Item1\", " \
			"\"value\": \"3\", \"default\": \"3\", " \
			"\"description\": \"First Item\", " \
			"\"group\" : \"Group1\", " \
			"\"rule\" : \"1 = 0\", " \
			"\"deprecated\" : \"false\", " \
			"\"order\": \"10\"} "
		"}";

const char *json_quotedSpecial = R"QS({ "key" : "test \"a\"", "description" : "Test \"description\"", "value" : {"description" : { "description" : "The description of this \"Fledge\" service", "type" : "string", "value" : "The \"Fledge\" admini\\strative API", "default" : "The \"Fledge\" administra\tive API" }, "name" : { "description" : "The name of this \"Fledge\" service", "type" : "string", "value" : "\"Fledge\"", "default" : "\"Fledge\"" }, "complex" : { "description" : "A JSON configuration parameter", "type" : "json", "value" : {"first":"Fledge","second":"json"}, "default" : {"first":"Fledge","second":"json"} }} })QS";

const char *json_parse_error = "{\"description\": {"
		"\"value\": \"The Fledge administrative API\","
		"\"type\": \"string\","
		"\"default\": \"The Fledge administrative API\","
		"\"description\": \"The description of this Fledge service\"},"
	"\"name\": {"
		"\"value\": \"Fledge\","
		"\"type\": \"string\","
		"\"default\": \"Fledge\","
		"\"description\": \"The name of this Fledge service\"},"
		"error : here,"
        "\"complex\": {" \
		"\"value\": { \"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"type\": \"json\","
		"\"default\": {\"first\" : \"Fledge\", \"second\" : \"json\" },"
		"\"description\": \"A JSON configuration parameter\"}}";

TEST(CategoriesTest, Count)
{
	ConfigCategories confCategories(categories);
	ASSERT_EQ(2, confCategories.length());
}

TEST(CategoriesTestQuoted, CountQuoted)
{
EXPECT_EXIT({
	ConfigCategories confCategories(categories_quoted);
	int num = confCategories.length();
	if (num != 2)
	{
		cerr << "CountQuoted is not 2" << endl;
	}
	exit(!(num == 2)); }, ::testing::ExitedWithCode(0), "");
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

TEST(CategoriesTestQuoted, toJSONQuoted)
{
	ConfigCategories categories;
	ConfigCategoryDescription *one = new ConfigCategoryDescription(string("cat\"1\""), string("desc\"1\""));
	ConfigCategoryDescription *two = new ConfigCategoryDescription(string("cat\"2\""), string("desc\"2\""));
	categories.addCategoryDescription(one);
	categories.addCategoryDescription(two);
	string result =  categories.toJSON();
	ASSERT_EQ(2, categories.length());
	ASSERT_EQ(0, result.compare(allCategories_quoted));
}

TEST(CategoriesTest, toJSONParameters)
{
	// Arrange
	ConfigCategory category("test_toJSONParameters", myCategory_to_json_parameters);

	// Act
	string strJSONFalse = category.toJSON();
	string strJSONTrue = category.toJSON(true);

	// Assert
	ASSERT_EQ(string::npos, strJSONFalse.find("order"));
	ASSERT_EQ(string::npos, strJSONFalse.find("readonly"));

	ASSERT_NE(string::npos, strJSONTrue.find("order"));
	ASSERT_NE(string::npos, strJSONTrue.find("readonly"));
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
EXPECT_EXIT({
	ConfigCategory confCategory("test", myCategory);
	bool ret = confCategory.getValue("name").compare("Fledge") == 0;
	if (!ret)
	{
		cerr << "getValue failed" << endl;
	}
	exit(!ret); }, ::testing::ExitedWithCode(0), "");
}

TEST(CategoryTest, getType)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(0, confCategory.getType("name").compare("string"));
}

TEST(CategoryTest, getDefault)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(0, confCategory.getDefault("name").compare("Fledge"));
}

TEST(CategoryTest, getDescription)
{
	ConfigCategory confCategory("test", myCategory);
	ASSERT_EQ(0, confCategory.getDescription("name").compare("The name of this Fledge service"));
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

TEST(CategoryTestQuoted, toJSONQuoted)
{
	ConfigCategory confCategory("test \"a\"", myCategory_quoted);
	confCategory.setDescription("Test \"description\"");
	ASSERT_EQ(0, confCategory.toJSON().compare(json_quoted));
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
EXPECT_EXIT({
	bool ret = false;
	try
	{
		ConfigCategory confCategory("test", myCategory_JSON_type_without_escaped_default);
		confCategory.setDescription("Test description");

		// test fails here!
		cerr << "setting confCategory must fail" << endl;
	}
	catch (exception *e)
	{
		ret = true;
		delete e;
		// Test ok; exception found
	} 
	catch (...)
	{
		ret = true;
		// Test ok; exception found
	}
	exit(!ret); }, ::testing::ExitedWithCode(0), "");
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
	ASSERT_EQ("My Fledge", confCategory.getDisplayName("name"));
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

/**
 * Test "script" type item
 */
TEST(CategoryTest, scriptItem)
{
	string file = "/home/ubuntu/source/develop/Fledge/data/scripts/pumpa_powerfilter_script_file27.py";
	ConfigCategory scriptCategory("script", myCategoryScript);
	ConfigCategory newCategory("scriptNew", scriptCategory.itemsToJSON(true));
	// Check we have file attribute in Category object
	ASSERT_EQ(0,
		  scriptCategory.getItemAttribute("script",
						  ConfigCategory::FILE_ATTR).compare(file));

	// Check we have 4 items in Category object
	ASSERT_EQ(4, newCategory.getCount());
}

/**
 * Check a cateogy object with oder, displayName etc
 */
TEST(CategoryTest, categoryAllFullOutput)
{
	ConfigCategory fullItems("full", myCategoryEnumFull);
	// Get all hidden objects
	string fullCategoryItems = fullItems.itemsToJSON(true);
	// Create a Category object from a JSON with all objects
	fullItems = ConfigCategory("full", fullCategoryItems);
	// Get standard objects
	string categoryItems = fullItems.itemsToJSON(false);
	// Check category has all hidden objects
	ASSERT_EQ(0, fullCategoryItems.compare(fullItems.itemsToJSON(true)));
	// Check basic category object has no hidden objects
	ASSERT_EQ(0, categoryItems.compare(fullItems.itemsToJSON(false)));
	// Check we have 4 items in Category object
	ASSERT_EQ(4, fullItems.getCount());
}

/**
 * Check all return values of a category
 */
TEST(CategoryTest, categoryValues)
{
        ConfigCategory complex("complex", bigCategory);
        ASSERT_EQ(true, complex.isBool("compression"));
        ASSERT_EQ(true, complex.isEnumeration("source"));
        ASSERT_EQ(true, complex.isString("plugin"));
        ASSERT_EQ(true, complex.getValue("plugin").compare("OMF") == 0);
        ASSERT_EQ(true, complex.getValue("OMFMaxRetry").compare("3") == 0);
}


/**
 * Test optional attributes
 */
TEST(CategoryTest, optionalItems)
{
	ConfigCategory category("optional", optionals);
	ASSERT_EQ(0, category.getItemAttribute("item1", ConfigCategory::GROUP_ATTR).compare("Group1"));
	ASSERT_EQ(0, category.getItemAttribute("item1", ConfigCategory::DEPRECATED_ATTR).compare("false"));
	ASSERT_EQ(0, category.getItemAttribute("item1", ConfigCategory::RULE_ATTR).compare("1 = 0"));
	ASSERT_EQ(0, category.getItemAttribute("item1", ConfigCategory::DISPLAY_NAME_ATTR).compare("Item1"));
}

/**
 * Special quotes for \\s and \\t
 */

TEST(CategoryTestQuoted, toJSONQuotedSpecial)
{
	ConfigCategory confCategory("test \"a\"", myCategory_quotedSpecial);
	confCategory.setDescription("Test \"description\"");
	ASSERT_EQ(0, confCategory.toJSON().compare(json_quotedSpecial));
}

TEST(Categorytest, parseError)
{
	EXPECT_THROW(ConfCategory("parseTest", json_parse_error), ConfigMalformed);
}

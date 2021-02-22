#include <gtest/gtest.h>
#include <reading.h>
#include <reading_set.h>
#include <omf.h>
#include <rapidjson/document.h>
#include <simple_https.h>

/*
 * Fledge Readings to OMF translation unit tests
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

using namespace std;
using namespace rapidjson;

#define TYPE_ID 1234

// 2 readings JSON text
const char *af_hierarchy_test01 = R"(
{
	"names" :
			{
					"3814_asset2" : "/Building1/EastWing/GroundFloor/Room4",
					"3814_asset3" : "Room14",
					"3814_asset4" : "names_asset4"
			},
	"metadata" : {
		"exist" : {
			"sinusoid4"     : "md_asset4",
			"sinusoid4_1"   : "md_asset4_1",
			"sinusoid2"     : "md_asset5"
		}
	}
}
)";

const char *af_hierarchy_test02 = R"(
{
}
)";

map<std::string, std::string> af_hierarchy_check01 ={
	// Asset_name   - Asset Framework path
	{"3814_asset2",         "/Building1/EastWing/GroundFloor/Room4"},
	{"3814_asset3",         "Room14"},
	{"3814_asset4",         "names_asset4"}
};

map<std::string, std::string> af_hierarchy_check02 ={

	// Asset_name   - Asset Framework path
	{"sinusoid4",         "md_asset4"},
	{"sinusoid4_1",       "md_asset4_1"},
	{"sinusoid2",         "md_asset5"}
};

map<std::string, std::string> af_hierarchy_check03 ={

	// Asset_name   - Asset Framework path
	{"sinusoid4",         "md_asset4"}
};


// 2 readings JSON text
const char *two_readings = R"(
    {
        "count" : 2, "rows" : [
            {
                "id": 1, "asset_code": "luxometer",
                "reading": { "lux": 45204.524 },
                "user_ts": "2018-06-11 14:00:08.532958",
                "ts": "2018-06-12 14:47:18.872708"
            },
            {
                "id": 2, "asset_code": "luxometer",
                "reading": { "lux": 76834.361 },
                "user_ts": "2018-08-21 14:00:09.32958",
                "ts": "2018-08-22 14:48:18.72708"
            }
        ]
    }
)";

// 2 readings JSON text
const char *readings_with_different_datapoints = R"(
    {
        "count" : 2, "rows" : [
            {
                "id": 1, "asset_code": "A",
                "reading": { "lux": 45204.524 },
                "user_ts": "2018-06-11 14:00:08.532958",
                "ts": "2018-06-12 14:47:18.872708"
            },
            {
                "id": 2, "asset_code": "A",
                "reading": { "temp": 23, "label" : "device_1" },
                "user_ts": "2018-08-21 14:00:09.32958",
                "ts": "2018-08-22 14:48:18.72708"
            }
        ]
    }
)";

// 3 readings JSON text with unsupported data types (array)
const char *all_readings_with_unsupported_datapoints_types = R"(
    {
        "count" : 4, "rows" : [
            {
                "id": 1, "asset_code": "A",
                "reading": { "lux": [45204.524] },
                "user_ts": "2018-06-11 14:00:08.532958",
                "ts": "2018-06-12 14:47:18.872708"
            },
            {
                "id": 2, "asset_code": "B",
                "reading": { "temp": [87], "label" : [1] },
                "user_ts": "2018-08-21 14:00:09.32958",
                "ts": "2018-08-22 14:48:18.72708"
            },
            {
                "id": 3, "asset_code": "C",
                "reading": { "temp": [23.2], "label" : [5] },
                "user_ts": "2018-08-21 14:00:09.32958",
                "ts": "2018-08-22 15:48:18.72708"
	    }
        ]
    }
)";

// 5 readings JSON text with unsupported data types (array)
const char *readings_with_unsupported_datapoints_types = R"(
    {
        "count" : 4, "rows" : [
            {
                "id": 1, "asset_code": "A",
                "reading": { "lux": [45204.524] },
                "user_ts": "2018-06-11 14:00:08.532958",
                "ts": "2018-06-12 14:47:18.872708"
            },
            {
                "id": 2, "asset_code": "B",
                "reading": { "temp": 87, "label" : [1] },
                "user_ts": "2018-08-21 14:00:09.32958",
                "ts": "2018-08-22 14:48:18.72708"
            },
            {
                "id": 3, "asset_code": "C",
                "reading": { "temp": [23.2], "label" : [5] },
                "user_ts": "2018-08-21 14:00:09.32958",
                "ts": "2018-08-22 15:48:18.72708"
            },
            {
                "id": 3, "asset_code": "D",
                "reading": { "temp": 23.2, "label" : 5 },
                "user_ts": "2018-08-21 14:00:09.32958",
                "ts": "2018-08-22 15:48:18.72708"
            },
            {
                "id": 3, "asset_code": "E",
                "reading": { "temp": [23.2], "label" : [5] },
                "user_ts": "2018-08-21 14:00:09.32958",
                "ts": "2018-08-22 15:48:18.72708"
            }
        ]
    }
)";


// 2 readings translated to OMF JSON text
const string two_translated_readings = "[{\"containerid\": \"" + to_string(TYPE_ID) + \
					"measurement_luxometer\", \"values\": [{\"lux\": "
					"45204.524, \"Time\": \"2018-06-11T14:00:08.532958Z\"}]}, "
					"{\"containerid\": \"" + to_string(TYPE_ID) + \
					"measurement_luxometer\", \"values\": "
					"[{\"lux\": 76834.361, \"Time\": \"2018-08-21T14:00:09.329580Z\"}]}]";

// Compare translated readings with a provided JSON value
TEST(OMF_transation, TwoTranslationsCompareResult)
{
	// Build a ReadingSet from JSON
	ReadingSet readingSet(two_readings);

        ostringstream jsonData;
        jsonData << "[";

	// Iterate over Readings via readingSet.getAllReadings()
	for (vector<Reading *>::const_iterator elem = readingSet.getAllReadings().begin();
							elem != readingSet.getAllReadings().end();
							++elem)
	{
		// Add into JSON string the OMF transformed Reading data
		jsonData << OMFData(**elem, TYPE_ID).OMFdataVal() << (elem < (readingSet.getAllReadings().end() - 1 ) ? ", " : "");
	}

	jsonData << "]";

	// Compare translation
	ASSERT_EQ(0, jsonData.str().compare(two_translated_readings));
}

// Create ONE reading, convert it and run checks
TEST(OMF_transation, OneReading)
{
	ostringstream jsonData;
	string strVal("printer");
        DatapointValue value(strVal);
	// ONE reading
	Reading lab("lab", new Datapoint("device", value));

	// Add another datapoint
	DatapointValue id((long) 3001);
	lab.addDatapoint(new Datapoint("id", id));

	// Create the OMF Json data
	jsonData << "[";
	jsonData << OMFData(lab, TYPE_ID).OMFdataVal();
	jsonData << "]";

	// "values" key is in the output 
	ASSERT_NE(jsonData.str().find(string("\"values\" : { ")), 0);

	// Parse JSON of translated data
        Document doc;
        doc.Parse(jsonData.str().c_str());
	if (doc.HasParseError())
	{
		ASSERT_FALSE(true);
	}
	else
	{
		// JSON is an array
		ASSERT_TRUE(doc.IsArray());
		// Array size is 1
		ASSERT_EQ(doc.Size(), 1);

		// Get element 0 of the array
		Value::ConstValueIterator itr = doc.Begin();

		// Check it's an object
		ASSERT_TRUE(itr->IsObject());
		// It has "containerid" and "values"
		ASSERT_TRUE(itr->HasMember("containerid") && itr->HasMember("values"));

		// "values" is an array
		ASSERT_TRUE((*itr)["values"].IsArray());
		// The array element [0] is an object with 3 keys
		ASSERT_EQ((*itr)["values"].GetArray()[0].GetObject().MemberCount(), 3);
	}
}

// Compare translated readings with a provided JSON value
TEST(OMF_transation, SuperSet)
{
	SimpleHttps sender("0.0.0.0:0", 10, 10, 10, 1);
	OMF omf(sender, "/", 1, "ABC");
	// Build a ReadingSet from JSON
	ReadingSet readingSet(readings_with_different_datapoints);
	vector<Reading *>readings = readingSet.getAllReadings();

	std::map<string, Reading*> superSetDataPoints;

	// Create a superset of all found datapoints for each assetName
	// the superset[assetName] is then passed to routines which handle
	// creation of OMF data types
	omf.setMapObjectTypes(readings, superSetDataPoints);

	// We have only 1 superset reading as the readings in input
	// have same assetName
	ASSERT_EQ(1, superSetDataPoints.size());
	auto it = superSetDataPoints.begin();
	// We have 3 datapoints in total in te superset
	ASSERT_EQ(3, (*it).second->getDatapointCount());
	omf.unsetMapObjectTypes(superSetDataPoints);
	// Superset map is empty
	ASSERT_EQ(0, superSetDataPoints.size());
}

// Compare translated readings with a provided JSON value
TEST(OMF_transation, AllReadingsWithUnsupportedTypes)
{
	// Build a ReadingSet from JSON
	ReadingSet readingSet(all_readings_with_unsupported_datapoints_types);

	ostringstream jsonData;
	jsonData << "[";

	bool pendingSeparator = false;
	// Iterate over Readings via readingSet.getAllReadings()
	for (auto elem = readingSet.getAllReadings().begin();
	     elem != readingSet.getAllReadings().end();
	     ++elem)
	{
		string rData =  OMFData(**elem, TYPE_ID).OMFdataVal();
		// Add into JSON string the OMF transformed Reading data
		if (!rData.empty())
		{
			jsonData << (pendingSeparator ? ", " : "") << rData;
			pendingSeparator = true;
		}
	}

	jsonData << "]";

	Document doc;
	doc.Parse(jsonData.str().c_str());
	if (doc.HasParseError())
	{
		ASSERT_FALSE(true);
	}
	else
	{
		// JSON is an array
		ASSERT_TRUE(doc.IsArray());
		// Array size is 1
		ASSERT_EQ(doc.Size(), 0);
	}
}

// Compare translated readings with a provided JSON value
TEST(OMF_transation, ReadingsWithUnsupportedTypes)
{
	// Build a ReadingSet from JSON
	ReadingSet readingSet(readings_with_unsupported_datapoints_types);

	ostringstream jsonData;
	jsonData << "[";

	bool pendingSeparator = false;
	// Iterate over Readings via readingSet.getAllReadings()
	for (auto elem = readingSet.getAllReadings().begin();
	     elem != readingSet.getAllReadings().end();
	     ++elem)
	{
		string rData =  OMFData(**elem, TYPE_ID).OMFdataVal();
		// Add into JSON string the OMF transformed Reading data
		if (!rData.empty())
		{
			jsonData << (pendingSeparator ? ", " : "") << rData;
			pendingSeparator = true;
		}
	}

	jsonData << "]";

	Document doc;
	doc.Parse(jsonData.str().c_str());
	if (doc.HasParseError())
	{
		ASSERT_FALSE(true);
	}
	else
	{
		// JSON is an array
		ASSERT_TRUE(doc.IsArray());
		// Array size is 1
		ASSERT_EQ(doc.Size(), 2);
	}
}

// Test the Asset Framework hierarchy fucntionlities
TEST(OMF_AfHierarchy, HandleAFMapNamesGood)
{
	Document JSon;

	map<std::string, std::string> NamesRules;
	map<std::string, std::string> MetadataRulesExist;

	bool AFMapEmptyNames;
	bool AFMapEmptyMetadata;

	// Dummy initializations
	SimpleHttps sender("0.0.0.0:0", 10, 10, 10, 1);
	OMF omf(sender, "/", 1, "ABC");

	omf.setAFMap(af_hierarchy_test01);

	NamesRules = omf.getNamesRules();
	MetadataRulesExist = omf.getMetadataRulesExist();

	// Test
	ASSERT_EQ(NamesRules,         af_hierarchy_check01);
	ASSERT_EQ(MetadataRulesExist, af_hierarchy_check02);

	AFMapEmptyNames = omf.getAFMapEmptyNames();
	AFMapEmptyMetadata = omf.getAFMapEmptyMetadata();

	ASSERT_EQ(AFMapEmptyNames, false);
	ASSERT_EQ(AFMapEmptyMetadata, false);
}

TEST(OMF_AfHierarchy, HandleAFMapEmpty)
{
	Document JSon;

	map<std::string, std::string> NamesRules;
	map<std::string, std::string> MetadataRulesExist;

	bool AFMapEmptyNames;
	bool AFMapEmptyMetadata;

	// Dummy initializations
	SimpleHttps sender("0.0.0.0:0", 10, 10, 10, 1);
	OMF omf(sender, "/", 1, "ABC");
	
	// Test
	omf.setAFMap(af_hierarchy_test02);

	AFMapEmptyNames = omf.getAFMapEmptyNames();
	AFMapEmptyMetadata = omf.getAFMapEmptyMetadata();

	ASSERT_EQ(AFMapEmptyNames, true);
	ASSERT_EQ(AFMapEmptyMetadata, true);
}

TEST(OMF_AfHierarchy, HandleAFMapNamesBad)
{
	Document JSon;

	map<std::string, std::string> MetadataRulesExist;
	
	// Dummy initializations
	SimpleHttps sender("0.0.0.0:0", 10, 10, 10, 1);
	OMF omf(sender, "/", 1, "ABC");

	omf.setAFMap(af_hierarchy_test01);
	MetadataRulesExist = omf.getMetadataRulesExist();

	// Test 02
	ASSERT_NE(MetadataRulesExist, af_hierarchy_check03);
}

// Test PI Server naming rules for invalid chars - Control characters plus: * ? ; { } [ ] | \ ` ' "
TEST(PiServer_NamingRules, NamingRulesCheck)
{
	// Dummy initializations
	SimpleHttps sender("0.0.0.0:0", 10, 10, 10, 1);
	OMF omf(sender, "/", 1, "ABC");

	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_1"), "asset_1");

	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_*1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_?1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_;1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_{1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_}1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_[1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_]1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_|1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_\\1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_`1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_'1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_\"1"), "asset__1");

	ASSERT_EQ(omf.ApplyPIServerNamingRules("_asset_1"), "_asset_1");

	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_\t1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_\n1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_\b1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_\r1"), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRules("asset_\\1"), "asset__1");
}
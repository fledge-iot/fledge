#include <gtest/gtest.h>
#include <reading.h>
#include <reading_set.h>
#include <omf.h>
#include <rapidjson/document.h>
#include <simple_https.h>
#include <OMFHint.h>
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

const char *OMFHint_readings_variable_handling_1 = R"(
    {
        "count" : 1, "rows" : [
            {
                "id": 1, "asset_code": "fogbench_luxometer",
                "reading": { "lux": [45204.524], "site":"Suez" ,"OMFHint": {"AFLocation":"/Sites/Orange/${site:unknown}/ADN C1"} },
                "user_ts": "2018-06-11 14:00:08.532958",
                "ts": "2018-06-12 14:47:18.872708"
            }
        ]
    }
)";

const char *OMFHint_readings_variable_handling_2 = R"(
    {
        "count" : 1, "rows" : [
            {
                "id": 1, "asset_code": "fogbench_pressure",
                "reading": { "pressure": [951.8],"site":"Trackonomy","OMFHint": {"AFLocation":"/Sites/Orange/${site:unknown}/ADN C1"} },
                "user_ts": "2018-06-11 14:00:08.532958",
                "ts": "2018-06-12 14:47:18.872708"
            }
        ]
    }
)";

const char *OMFHint_readings_variable_handling_3 = R"(
    {
        "count" : 1, "rows" : [
            {
                "id": 1, "asset_code": "fogbench_accelerometer",
                "reading": { "x": [951.8], "y": [951.8] },
                "user_ts": "2018-06-11 14:00:08.532958",
                "ts": "2018-06-12 14:47:18.872708"
            }
        ]
    }
)";

const char *OMFHint_readings_variable_handling_4 = R"(
    {
        "count" : 1, "rows" : [
            {
                "id": 1, "asset_code": "fogbench_accelerometer",
				"reading": { "lux": [45204.524], "site":"Suez" , "l1":"Sites_new" ,"OMFHint": {"AFLocation":"/${l1:Sites}/${l2:Orange}/${site:unknown}/ADN C1"} },

                "user_ts": "2018-06-11 14:00:08.532958",
                "ts": "2018-06-12 14:47:18.872708"
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
	string measurementId;

	// Build a ReadingSet from JSON
	ReadingSet readingSet(two_readings);

        ostringstream jsonData;
        jsonData << "[";

	// Iterate over Readings via readingSet.getAllReadings()
	for (vector<Reading *>::const_iterator elem = readingSet.getAllReadings().begin();
							elem != readingSet.getAllReadings().end();
							++elem)
	{
		measurementId = to_string(TYPE_ID) + "measurement_luxometer";

		// Add into JSON string the OMF transformed Reading data
		jsonData << OMFData(**elem, measurementId).OMFdataVal() << (elem < (readingSet.getAllReadings().end() - 1 ) ? ", " : "");
	}

	jsonData << "]";

	// Compare translation
	ASSERT_EQ(0, jsonData.str().compare(two_translated_readings));
}

// Create ONE reading, convert it and run checks
TEST(OMF_transation, OneReading)
{
	string measurementId;

	ostringstream jsonData;
	string strVal("printer");
        DatapointValue value(strVal);
	// ONE reading
	Reading lab("lab", new Datapoint("device", value));

	// Add another datapoint
	DatapointValue id((long) 3001);
	lab.addDatapoint(new Datapoint("id", id));

	measurementId = "dummy";

	// Create the OMF Json data
	jsonData << "[";
	jsonData << OMFData(lab, measurementId).OMFdataVal();
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
	string measurementId;

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
		measurementId = "dummy";

		string rData =  OMFData(**elem, measurementId).OMFdataVal();
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
	string measurementId;

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
		measurementId = "dummy";

		string rData =  OMFData(**elem, measurementId).OMFdataVal();
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
	bool changed = false;

	// Dummy initializations
	SimpleHttps sender("0.0.0.0:0", 10, 10, 10, 1);
	OMF omf(sender, "/", 1, "ABC");

	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_1", &changed), "asset_1");
	ASSERT_EQ(changed, false);

	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_*1", &changed), "asset__1");
	ASSERT_EQ(changed, true);

	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_?1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_;1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_{1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_}1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_[1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_]1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_|1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_\\1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_`1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_'1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_\"1", &changed), "asset__1");

	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("_asset_1", &changed), "_asset_1");
	ASSERT_EQ(changed, false);

	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_\t1", &changed), "asset__1");
	ASSERT_EQ(changed, true);

	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_\n1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_\b1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_\r1", &changed), "asset__1");
	ASSERT_EQ(omf.ApplyPIServerNamingRulesInvalidChars("asset_\\1", &changed), "asset__1");
}

TEST(PiServer_NamingRules, Suffix)
{
	string assetName;
	// Dummy initializations
	SimpleHttps sender("0.0.0.0:0", 10, 10, 10, 1);
	OMF omf(sender, "/", 1, "ABC");

	assetName = "asset_1";

	omf.setNamingScheme(NAMINGSCHEME_CONCISE);
	ASSERT_EQ(omf.generateSuffixType(assetName, 1), "");
	ASSERT_EQ(omf.generateSuffixType(assetName, 2), "-type2");
	ASSERT_EQ(omf.generateSuffixType(assetName, 3), "-type3");

	omf.setNamingScheme(NAMINGSCHEME_SUFFIX);
	ASSERT_EQ(omf.generateSuffixType(assetName, 1), "-type1");
	ASSERT_EQ(omf.generateSuffixType(assetName, 2), "-type2");
	ASSERT_EQ(omf.generateSuffixType(assetName, 3), "-type3");

	omf.setNamingScheme(NAMINGSCHEME_HASH);
	ASSERT_EQ(omf.generateSuffixType(assetName, 1), "");
	ASSERT_EQ(omf.generateSuffixType(assetName, 2), "-type2");
	ASSERT_EQ(omf.generateSuffixType(assetName, 3), "-type3");

	omf.setNamingScheme(NAMINGSCHEME_COMPATIBILITY);
	ASSERT_EQ(omf.generateSuffixType(assetName, 1), "-type1");
	ASSERT_EQ(omf.generateSuffixType(assetName, 2), "-type2");
	ASSERT_EQ(omf.generateSuffixType(assetName, 3), "-type3");
}

TEST(PiServer_NamingRules, Prefix)
{
	string asset;

	// Dummy initializations
	SimpleHttps sender("0.0.0.0:0", 10, 10, 10, 1);
	OMF omf(sender, "/", 1, "ABC");

	asset="asset_1";

	{ // ENDPOINT_PIWEB_API

		omf.setPIServerEndpoint(ENDPOINT_PIWEB_API);
		omf.setNamingScheme(NAMINGSCHEME_CONCISE);
		ASSERT_EQ(omf.generateMeasurementId(asset), asset);

		omf.setNamingScheme(NAMINGSCHEME_SUFFIX);
		ASSERT_EQ(omf.generateMeasurementId(asset), asset);

		omf.setNamingScheme(NAMINGSCHEME_HASH);
		ASSERT_EQ(omf.generateMeasurementId(asset), "_1measurement_" + asset);

		omf.setNamingScheme(NAMINGSCHEME_COMPATIBILITY);
		ASSERT_EQ(omf.generateMeasurementId(asset), "_1measurement_" + asset);
	}

	{ // ENDPOINT_EDS

		omf.setPIServerEndpoint(ENDPOINT_EDS);
		omf.setNamingScheme(NAMINGSCHEME_CONCISE);
		ASSERT_EQ(omf.generateMeasurementId(asset), asset);

		omf.setNamingScheme(NAMINGSCHEME_SUFFIX);
		ASSERT_EQ(omf.generateMeasurementId(asset), asset);

		omf.setNamingScheme(NAMINGSCHEME_HASH);
		ASSERT_EQ(omf.generateMeasurementId(asset), "1measurement_" + asset);

		omf.setNamingScheme(NAMINGSCHEME_COMPATIBILITY);
		ASSERT_EQ(omf.generateMeasurementId(asset), "1measurement_" + asset);
	}
}

TEST(OMF_hints, m_chksum)
{
	string asset;

	// Case - test case having unexpected result
	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"AFLocation\":\"/Sites/Orange/Suez/ADN C1\"}"),
		""
	);

	// Case - single rule
	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"AFLocation\":123}"),
		""
	);

	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"AFLocation\":\"/Sites/Orange/Suez/ADN C1\"}"),
		""
	);

	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"number\":\"float32\"}"),
		"{\"number\":\"float32\"}"
	);

	// Case - multi rules
	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"number\":\"float32\",\"AFLocation\":\"/Sites/Orange/Trackonomy/ADN C2\"}"),
		"{\"number\":\"float32\"}"
	);

	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"AFLocation\":\"/Sites/Orange/Trackonomy/ADN C2\",\"number\":\"float32\"}"),
		"{\"number\":\"float32\"}"
	);

	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"number\":\"float32\",\"AFLocation\":\"/Sites/Orange/Trackonomy/ADN C2\",\"number\":\"float32\"}"),
		"{\"number\":\"float32\",\"number\":\"float32\"}"
	);

	// Case - variables
	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"AFLocation\":\"/${l1:Sites}/${l2}/${site:unknown}/ADN C1\"}"),
		""
	);

	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"number\":\"float32\",\"AFLocation\":\"/${l1:Sites}/${l2}/${site:unknown}/ADN C1\"}"),
		"{\"number\":\"float32\"}"
	);

	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"AFLocation\":\"/${l1:Sites}/${l2}/${site:unknown}/ADN C1\",\"number\":\"float32\"}"),
		"{\"number\":\"float32\"}"
	);

	ASSERT_EQ(
		OMFHints::getHintForChecksum("{\"number\":\"float32\",\"AFLocation\":\"/${l1:Sites}/${l2}/${site:unknown}/ADN C1\",\"number\":\"float32\"}"),
		"{\"number\":\"float32\",\"number\":\"float32\"}"
	);
}

TEST(OMF_hints, variableHandling)
{
	string AFHierarchy;
	string AFHierarchyNew;

	{ // Case
		ReadingSet readingSet(OMFHint_readings_variable_handling_1);
		vector<Reading *> readings = readingSet.getAllReadings();

		AFHierarchy = "/Sites/Orange/${site:unknown}/ADN C1";
		vector<Reading *>::const_iterator elem = readings.begin();
		Reading *reading = *elem;
		AFHierarchyNew = OMF::variableValueHandle(*reading, AFHierarchy);
		ASSERT_EQ (AFHierarchyNew, "/Sites/Orange/Suez/ADN C1");
	}

	{ // Case
		ReadingSet readingSet(OMFHint_readings_variable_handling_2);
		vector<Reading *> readings = readingSet.getAllReadings();

		AFHierarchy = "/Sites/Orange/${site:unknown}/ADN C1";
		vector<Reading *>::const_iterator elem = readings.begin();
		Reading *reading = *elem;
		AFHierarchyNew = OMF::variableValueHandle(*reading, AFHierarchy);
		ASSERT_EQ (AFHierarchyNew, "/Sites/Orange/Trackonomy/ADN C1");
	}

	{ // Case
		ReadingSet readingSet(OMFHint_readings_variable_handling_3);
		vector<Reading *> readings = readingSet.getAllReadings();

		AFHierarchy = "/Sites/Orange/${site:unknown}/ADN C1";
		vector<Reading *>::const_iterator elem = readings.begin();
		Reading *reading = *elem;
		AFHierarchyNew = OMF::variableValueHandle(*reading, AFHierarchy);
		ASSERT_EQ (AFHierarchyNew, "/Sites/Orange/unknown/ADN C1");
	}

	{ // Case - multiple variables
		ReadingSet readingSet(OMFHint_readings_variable_handling_4);
		vector<Reading *> readings = readingSet.getAllReadings();

		AFHierarchy = "/${l1:Sites}/${l2:Orange}/${site:unknown}/ADN C1";
		vector<Reading *>::const_iterator elem = readings.begin();
		Reading *reading = *elem;
		AFHierarchyNew = OMF::variableValueHandle(*reading, AFHierarchy);
		ASSERT_EQ (AFHierarchyNew, "/Sites_new/Orange/Suez/ADN C1");
	}

	{ // Case - default not defined ${l3}
		ReadingSet readingSet(OMFHint_readings_variable_handling_4);
		vector<Reading *> readings = readingSet.getAllReadings();

		AFHierarchy = "/${l1:Sites}/${l3}/${site:unknown}/ADN C1";
		vector<Reading *>::const_iterator elem = readings.begin();
		Reading *reading = *elem;
		AFHierarchyNew = OMF::variableValueHandle(*reading, AFHierarchy);
		ASSERT_EQ (AFHierarchyNew, "/Sites_new/Suez/ADN C1");
	}

}

TEST(OMF_hints, variableExtract)
{
	bool found;
	string AFHierarchy, variable, value, deafult;

	// Case
	AFHierarchy= "/Sites/Orange/${site:unknown}/ADN C1";
	found = OMF::extractVariable(AFHierarchy, variable, value, deafult);
	ASSERT_EQ (found, true);
	ASSERT_EQ (variable, "${site:unknown}");
	ASSERT_EQ (value, "site");
	ASSERT_EQ (deafult, "unknown");

	// Case
	AFHierarchy= "/Sites/Orange/Trackonomy/ADN C1";
	found = OMF::extractVariable(AFHierarchy, variable, value, deafult);
	ASSERT_EQ (found, false);
	ASSERT_EQ (variable, "");
	ASSERT_EQ (value, "");
	ASSERT_EQ (deafult, "");

	// Case
	AFHierarchy= "${Trackonomy:unknown1}/Sites/Orange/ADN C1";
	found = OMF::extractVariable(AFHierarchy, variable, value, deafult);
	ASSERT_EQ (found, true);
	ASSERT_EQ (variable, "${Trackonomy:unknown1}");
	ASSERT_EQ (value, "Trackonomy");
	ASSERT_EQ (deafult, "unknown1");

	// Case
	AFHierarchy= "/Sites/Orange/ADN C1/${Orange:unknown12}";
	found = OMF::extractVariable(AFHierarchy, variable, value, deafult);
	ASSERT_EQ (found, true);
	ASSERT_EQ (variable, "${Orange:unknown12}");
	ASSERT_EQ (value, "Orange");
	ASSERT_EQ (deafult, "unknown12");
}
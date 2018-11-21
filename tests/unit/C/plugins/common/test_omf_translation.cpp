#include <gtest/gtest.h>
#include <reading.h>
#include <reading_set.h>
#include <omf.h>
#include <rapidjson/document.h>

/*
 * FogLAMP Readings to OMF translation unit tests
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

using namespace std;
using namespace rapidjson;

#define TYPE_ID "1234"

// 2 readings JSON text
const char *two_readings = R"(
    {
        "count" : 2, "rows" : [
            {
                "id": 1, "asset_code": "luxometer",
                "read_key": "5b3be500-ff95-41ae-b5a4-cc99d08bef4a",
                "reading": { "lux": 45204.524 },
                "user_ts": "2018-06-11 14:00:08.532958",
                "ts": "2018-06-12 14:47:18.872708"
            },
            {
                "id": 2, "asset_code": "luxometer",
                "read_key": "5b3be50c-ff95-41ae-b5a4-cc99d08bef4a",
                "reading": { "lux": 76834.361 },
                "user_ts": "2018-08-21 14:00:09.32958",
                "ts": "2018-08-22 14:48:18.72708"
            }
        ]
    }
)";


// 2 readings translated to OMF JSON text
const char *two_translated_readings = R"([{"containerid": ")" TYPE_ID R"(measurement_luxometer", "values": [{"lux": 45204.524, "Time": "2018-06-11T14:00:08.532958Z"}]}, {"containerid": ")" TYPE_ID R"(measurement_luxometer", "values": [{"lux": 76834.361, "Time": "2018-08-21T14:00:09.329580Z"}]}])";

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
		jsonData << OMFData(**elem, string(TYPE_ID)).OMFdataVal() << (elem < (readingSet.getAllReadings().end() - 1 ) ? ", " : "");
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
	jsonData << OMFData(lab, string(TYPE_ID)).OMFdataVal();
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

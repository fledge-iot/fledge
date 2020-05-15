/*
 * unit tests - Fledge Readings to OMF translation having PI Web API as end-point
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <gtest/gtest.h>
#include <reading.h>
#include <reading_set.h>
#include <omf.h>
#include <rapidjson/document.h>
#include <simple_https.h>

using namespace std;
using namespace rapidjson;

#define TO_STRING(...) DEFER(TO_STRING_)(__VA_ARGS__)
#define DEFER(x) x
#define TO_STRING_(...) #__VA_ARGS__
#define QUOTE(...) TO_STRING(__VA_ARGS__)

#define TYPE_ID             1234
#define AF_HIERARCHY_1LEVEL "fledge_data_piwebapi"
#define CONTAINER_ID        "fledge_data_piwebapi_1234measurement_luxometer"

// 2 readings JSON text
const char *pi_web_api_two_readings = R"(
    {
        "count" : 2, "rows" : [
            {
                "id": 1, "asset_code": "luxometer",
                "reading": { "lux": 45204.524 },
                "user_ts": "2018-06-11 14:00:08.532958",
                "ts": "2add_subdirectory(tests/unit/C/common)018-06-12 14:47:18.872708"
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

// 2 readings translated to OMF JSON text
const char *pi_web_api_two_translated_readings = QUOTE(
	[{"containerid": CONTAINER_ID,
		"values": [{"lux": 45204.524, "Time": "2018-06-11T14:00:08.532958Z"}]},
  	 {"containerid": CONTAINER_ID,
		"values": [{"lux": 76834.361, "Time": "2018-08-21T14:00:09.329580Z"}]}]
);


// Compare translated readings with a provided JSON value
TEST(PIWEBAPI_OMF_transation, TwoTranslationsCompareResult)
{
	// Build a ReadingSet from JSON
	ReadingSet readingSet(pi_web_api_two_readings);

	ostringstream jsonData;
	jsonData << "[";

	const OMF_ENDPOINT PI_SERVER_END_POINT = ENDPOINT_PIWEB_API;

	// Iterate over Readings via readingSet.getAllReadings()
	for (vector<Reading *>::const_iterator elem = readingSet.getAllReadings().begin();
	     elem != readingSet.getAllReadings().end();
	     ++elem)
	{
		// Add into JSON string the OMF transformed Reading data
		jsonData << OMFData(**elem, TYPE_ID, PI_SERVER_END_POINT, AF_HIERARCHY_1LEVEL).OMFdataVal() << (elem < (readingSet.getAllReadings().end() - 1 ) ? ", " : "");
	}

	jsonData << "]";

	// Compare translation
	ASSERT_EQ(jsonData.str(), pi_web_api_two_translated_readings);
}



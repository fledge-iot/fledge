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

#include <piwebapi.h>


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
		jsonData << OMFData(**elem, CONTAINER_ID, PI_SERVER_END_POINT, AF_HIERARCHY_1LEVEL).OMFdataVal() << (elem < (readingSet.getAllReadings().end() - 1 ) ? ", " : "");
	}

	jsonData << "]";

	// Compare translation
	ASSERT_EQ(jsonData.str(), pi_web_api_two_translated_readings);

}

// Tests the handling of the PI Web API error message
TEST(PIWEBAPI_OMF_ErrorMessages, AllCases)
{
	PIWebAPI piWeb;
	string json;

	// Base case
	ASSERT_EQ(piWeb.errorMessageHandler("x x x"),"x x x");

	// Handles error message substitution
	ASSERT_EQ(piWeb.errorMessageHandler("Noroutetohost"),"The PI Web API server is not reachable, verify the network reachability");
	ASSERT_EQ(piWeb.errorMessageHandler("Failedtosenddata:Noroutetohost"),"The PI Web API server is not reachable, verify the network reachability");

	// Handles HTTP error code recognition
	ASSERT_EQ(piWeb.errorMessageHandler("n, HTTP code |503| HTTP error |<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML"),"503 Service Unavailable");

	// Handles error in JSON format returned by the PI Web API
	json = QUOTE(
		{
			"OperationId": "939b4d00-9041-48ee-9d50-d1365711706c",
			"Messages": [
				{
					"MessageIndex": 1,
					"Events": [
					{
						"EventInfo": {
							"Message": "Type does not have a property with the specified index.",
							"Reason": null,
							"Suggestions": [
							"Check that the correct type is being used.",
							"Check that no unexpected data loss has occurred."
							],
							"EventCode": 6021,
							"Parameters": [
							{
								"Name": "TypeId",
								"Value": "A_4273005507977094880_fledge_ihsdev_1_sin_4816_asset_1_typename_measurement"
							},
							{
								"Name": "TypeVersion",
								"Value": "1.0.0.0"
							},
							{
								"Name": "Property",
								"Value": "sinusoidB"
							}
							]
						},
						"ExceptionInfo": null,
						"Severity": "Info",
						"InnerEvents": []
					}
					],
					"Status": {
						"Code": 202,
						"HighestSeverity": "Info"
					}
				}
			]
		}
	);

	ASSERT_EQ(piWeb.errorMessageHandler(json),"Type does not have a property with the specified index. A_4273005507977094880_fledge_ihsdev_1_sin_4816_asset_1_typename_measurement 1.0.0.0 sinusoidB");


	json = QUOTE(
	{
		"OperationId": "4760dad2-c08b-4606-901a-4288f1ffd7da",
			"Messages": [
		{
			"MessageIndex": 0,
				"Events": [
			{
				"EventInfo": {
					"Message": "Type does not have a property with the specified index.",
						"Reason": null,
						"Suggestions": [
					"Check that the correct type is being used.",
						"Check that no unexpected data loss has occurred."
					],
					"EventCode": 6021,
						"Parameters": [
					{
						"Name": "TypeId",
							"Value": "A_4273005507977094880_fledge_ihsdev_1_sin_4816_asset_1_typename_measurement"
					},
					{
						"Name": "TypeVersion",
							"Value": "1.0.0.0"
					},
					{
						"Name": "Property",
							"Value": "sinusoidB"
					}
					]
				},
				"ExceptionInfo": null,
					"Severity": "Info",
					"InnerEvents": []
			}
			],
			"Status": {
				"Code": 202,
					"HighestSeverity": "Info"
			}
		}
		]
	}
	);

	ASSERT_EQ(piWeb.errorMessageHandler(json),"Type does not have a property with the specified index. A_4273005507977094880_fledge_ihsdev_1_sin_4816_asset_1_typename_measurement 1.0.0.0 sinusoidB");

	json = QUOTE(
		{
			"OperationId": "xcaa5120-ca94-4eda-934e-ffc7d368c6f6",
			"Messages": [
				{
				  "MessageIndex": 0,
				  "Events": [
					{
					  "EventInfo": {
						"Message": "Container not found.",
						"Reason": null,
						"Suggestions": [],
						"EventCode": 5002,
						"Parameters": [
						  {
							"Name": "ContainerId",
							"Value": "4273005507977094880_1measurement_sin_4816_asset_1"
						  }
						]
					  },
					  "ExceptionInfo": {
						"Type": "OSIsoft.OMF.Loggers.OmfLoggableException",
						"Message": "Container not found."
					  },
					  "Severity": "Error",
					  "InnerEvents": []
					}
				  ],
				  "Status": {
					"Code": 404,
					"HighestSeverity": "Error"
				  }
				}
			]
		}
	);

	// within bad characters
	ASSERT_EQ(piWeb.errorMessageHandler(": errorMsg  |HTTP code |404| HTTP error |\uFEFF" + json + "|"),"Container not found. 4273005507977094880_1measurement_sin_4816_asset_1");

	ASSERT_EQ(piWeb.errorMessageHandler(": errorMsg  |HTTP code |404| HTTP error |" + json + "|"),"Container not found. 4273005507977094880_1measurement_sin_4816_asset_1");

	json = QUOTE(
		{
			"OperationId": "xcaa5120-ca94-4eda-934e-ffc7d368c6f6",
			"Messages": [
			{
				"MessageIndex": 1
			},
			{
				"MessageIndex": 0,
				"Events": [
				{
					"EventInfo": {
						"Message": "Container not found.",
						"Reason": null,
						"Suggestions": [],
						"EventCode": 5002,
						"Parameters": [
						{
							"Name": "ContainerId",
							"Value": "4273005507977094880_1measurement_sin_4816_asset_1"
						}
						]
					},
					"ExceptionInfo": {
						"Type": "OSIsoft.OMF.Loggers.OmfLoggableException",
						"Message": "Container not found."
					},
					"Severity": "Error",
					"InnerEvents": []
				}
				],
				"Status": {
					"Code": 404,
					"HighestSeverity": "Error"
				}
			}
			]
		}
	);
	ASSERT_EQ(piWeb.errorMessageHandler(json),"Container not found. 4273005507977094880_1measurement_sin_4816_asset_1");

	// Handling reason
	json = QUOTE(
		{
			"OperationId": "f48a2233-86ba-45d2-9787-48e3e48be78a",
			"Messages": [
			{
				"MessageIndex": null,
				"Events": [
				{
					"EventInfo": {
						"Message": "An error parsing the OMF message(s) occurred.",
						"Reason": "The OMF request body was unable to be parsed.",
						"Suggestions": [
						"Check that the OMF request body is syntactically valid.",
						"Check that the request only uses features available in the OMF version specified by the 'omfversion' header."
						],
						"EventCode": 3002,
						"Parameters": []
					},
					"ExceptionInfo": {
						"Type": "OSIsoft.OMF.Loggers.OmfLoggableException",
						"Message": "An error parsing the OMF message(s) occurred."
					},
					"Severity": "Error",
					"InnerEvents": [
					{
						"EventInfo": null,
						"ExceptionInfo": {
							"Type": "Newtonsoft.Json.JsonSerializationException",
							"Message": "Error converting value \"containerid\" to type 'OSIsoft.OMF.Specification.Models.V1_1.DataMessageDTO'. Path '[1]', line 1, position 247."
						},
						"Severity": null,
						"InnerEvents": [
						{
							"EventInfo": null,
							"ExceptionInfo": {
								"Type": "System.ArgumentException",
								"Message": "Could not cast or convert from System.String to OSIsoft.OMF.Specification.Models.V1_1.DataMessageDTO."
							},
							"Severity": null,
							"InnerEvents": []
						}
						]
					}
					]
				}
				],
				"Status": {
					"Code": 400,
					"HighestSeverity": "Error"
				}
			}
			]
		}
	);

	ASSERT_EQ(piWeb.errorMessageHandler(json),"An error parsing the OMF message(s) occurred. The OMF request body was unable to be parsed.");

}






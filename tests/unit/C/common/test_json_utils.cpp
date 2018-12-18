#include <gtest/gtest.h>
#include <string>
#include <vector>
#include "json_utils.h"

using namespace std;


const char *json_ok_2 =  "{" \
					"\"description\": "\
						"\"These errors are considered not blocking in the communication with the PI Server, " \
						  " the sending operation will proceed with the next block of data if one of these is encountered\" ," \
					"\"type\": \"JSON\", " \
					"\"errors400\": \"{\\\"errors400X\\\": "\
			                        "["\
				                        "\\\"Redefinition of the type with the same ID is not allowed\\\", "\
							"\\\"Invalid value type for the property\\\" "\
			                        "]"\
	                                "}\", " \
					"\"order\": \"17\" ,"  \
					"\"readonly\": \"true\" " \
			"} ";

const char *json_ok =  "{" \
					"\"description\":  "\
			                        "["\
				                        "\"Redefinition of the type with the same ID is not allowed\", "\
							"\"Invalid value type for the property\" "\
			                        "]"\
	                                ", " \
					"\"type\": \"JSON\", " \
					"\"order\": \"17\" ,"  \
					"\"readonly\": \"true\" " \
			"} ";

 
const char *json_bad = "{" \
			"\"notBlockingErrors\": {" \
				"\"description\": "\
					"\"These errors are considered not blocking in the communication with the PI Server, " \
					  " the sending operation will proceed with the next block of data if one of these is encountered\" ," \
				"\"type\": \"JSON\", " \
				"\"default\": \"{\\\"errors400\\\": "\
		                        "["\
			                        "\\\"Redefinition of the type with the same ID is not allowed\\\", "\
						"\\\"Invalid value type for the property\\\" "\
		                        "]"\
                                "xxxx";





TEST(JsonToVectorString, JSONok)
{
	std::vector<std::string> stringJSON;
	bool result;

	result = JSONStringToVectorString(stringJSON,json_ok,"description");

	ASSERT_EQ(result, true);
}

//TEST(JsonToVectorString, JSONbad)
//{
//	std::vector<std::string> stringJSON;
//	bool result;
//
//	result = JSONStringToVectorString(stringJSON,json_bad,"notBlockingErrors");
//
//	ASSERT_EQ(result, false);
//}
//
//TEST(JsonToVectorString, BadKey)
//{
//	std::vector<std::string> stringJSON;
//	bool result;
//
//	result = JSONStringToVectorString(stringJSON,json_ok,"xxx");
//
//	ASSERT_EQ(result, false);
//}
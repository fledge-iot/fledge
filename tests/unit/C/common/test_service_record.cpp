#include <gtest/gtest.h>
#include <service_record.h>
#include <string.h>
#include <string>

using namespace std;

/**
 * Creation of service record JSON
 */
TEST(ServiceRecordTest, JSON)
{
ServiceRecord serviceRecord("test1", "testType", "http", "localhost", 1234, 4321);
string json;
string expected("{ \"name\" : \"test1\",\"type\" : \"testType\",\"protocol\" : \"http\",\"address\" : \"localhost\",\"management_port\" : 4321,\"service_port\" : 1234 }");

	serviceRecord.asJSON(json);

	ASSERT_EQ(json.compare(expected), 0);
}


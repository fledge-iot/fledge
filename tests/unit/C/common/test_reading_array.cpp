/*
 * unit tests - FOGL-7748 : Support array data in reading json
 *
 * Copyright (c) 2023 Dianomic Systems, Inc.
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <gtest/gtest.h>
#include <datapoint.h>
#include <reading.h>
#include <vector>
#include <exception>
#include <string>

using namespace std;


const char *ReadingJSON = R"(
    {
        "floor1":30.25, "floor2":34.28, "floor3":[38.25,60.89,40.28]
    }
)";

const char *unsupportedReadingJSON = R"(
    {
        "floor1":[38,"error",40]
    }
)";

const char *NestedReadingJSON = R"(
{
	"pressure": {"floor1":30, "floor2":34, "floor3":[38,60,40] }
}
)";

TEST(TESTReading, TestUnspportedReadingForListType )
{
    try
    {
        vector<Reading *> readings;
        readings.push_back(new Reading("test", unsupportedReadingJSON));
        vector<Datapoint *>&dp = readings[0]->getReadingData();

        ASSERT_EQ(readings[0]->getDatapointCount(),1);
        ASSERT_EQ(readings[0]->getAssetName(),"test");
    }
    catch(exception& ex)
    {
        string msg(ex.what());
        ASSERT_EQ(msg,"Only numeric lists are currently supported in datapoints");
    }
   

}

TEST(TESTReading, TestReadingForListType )
{
    vector<Reading *> readings;
    readings.push_back(new Reading("test", ReadingJSON));
    vector<Datapoint *>&dp = readings[0]->getReadingData();

    ASSERT_EQ(readings[0]->getDatapointCount(),3);
    ASSERT_EQ(readings[0]->getAssetName(),"test");

    ASSERT_EQ(dp[0]->getName(),"floor1");
    ASSERT_EQ(dp[0]->getData().toDouble(),30.25);

    ASSERT_EQ(dp[1]->getName(),"floor2");
    ASSERT_EQ(dp[1]->getData().toDouble(),34.28);

    ASSERT_EQ(dp[2]->getName(),"floor3");
    ASSERT_EQ(dp[2]->getData().toString(),"[38.25, 60.89, 40.28]");
}

TEST(TESTReading, TestReadingForNestedListType )
{
    vector<Reading *> readings;
    readings.push_back(new Reading("test", NestedReadingJSON));
    vector<Datapoint *>&dp = readings[0]->getReadingData();

    ASSERT_EQ(readings[0]->getDatapointCount(),1);
    ASSERT_EQ(readings[0]->getAssetName(),"test");

    ASSERT_EQ(dp[0]->getName(),"pressure");
    ASSERT_EQ(dp[0]->getData().toString(),"{\"floor1\":30, \"floor2\":34, \"floor3\":[38, 60, 40]}");
    
}


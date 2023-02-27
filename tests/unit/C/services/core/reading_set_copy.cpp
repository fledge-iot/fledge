/*
 * unit tests - FOGL-7353 Fledge Copy ReadingSet
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
#include <reading_set.h>

using namespace std;

const char *ReadingJSON = R"(
    {
        "count" : 1, "rows" : [
            {
                "id": 1, "asset_code": "temperature",
                "reading": { "degrees": 200.65 },
                "user_ts": "2023-02-06 14:00:08.532958",
                "ts": "2023-02-06 14:47:18.872708"
            }
        ]
    }
)";

const char *NestedReadingJSON = R"(
    {
        "count" : 1, "rows" : [
            {
                "id": 1, "asset_code": "SiteStatus",
                "reading": { "degrees": [200.65,34.45,500.36],"pressure": {"floor1":30, "floor2":34, "floor3":36 } },
                "user_ts": "2023-02-06 14:00:08.532958",
                "ts": "2023-02-06 14:47:18.872708"
            }
        ]
    }
)";

TEST(READINGSET, DeepCopyCheckReadingFromNestedJSON)
{
    ReadingSet *readingSet1 = new ReadingSet(NestedReadingJSON);
    ReadingSet *readingSet2 = new ReadingSet();
    readingSet2->copy(*readingSet1);

    auto r1 = readingSet1->getAllReadings();
    auto dp1 = r1[0]->getReadingData();

    // Fetch nested datapoints
    ASSERT_EQ(dp1[0]->getName(), "degrees");
    ASSERT_EQ(dp1[0]->getData().toString(), "[200.65, 34.45, 500.36]");
    ASSERT_EQ(dp1[1]->getName(), "pressure");
    ASSERT_EQ(dp1[1]->getData().toString(), "{\"floor1\":30, \"floor2\":34, \"floor3\":36}");

    auto r2 = readingSet2->getAllReadings();
    auto dp2 = r2[0]->getReadingData();
    ASSERT_EQ(dp2[0]->getName(), "degrees");
    ASSERT_EQ(dp2[0]->getData().toString(), "[200.65, 34.45, 500.36]");
    ASSERT_EQ(dp2[1]->getName(), "pressure");
    ASSERT_EQ(dp2[1]->getData().toString(), "{\"floor1\":30, \"floor2\":34, \"floor3\":36}");

    // Check the address of datapoints
    ASSERT_NE(dp1[0], dp2[0]);
    ASSERT_NE(dp1[1], dp2[1]);

    // Confirm there is no error of double delete
    delete readingSet1;
    delete readingSet2;
}

TEST(READINGSET, DeepCopyCheckReadingFromJSON)
{
    ReadingSet *readingSet1 = new ReadingSet(ReadingJSON);
    ReadingSet *readingSet2 = new ReadingSet();
    readingSet2->copy(*readingSet1);

    delete readingSet1;

    // Fetch value after deleting readingSet1 to check readingSet2 is pointing to different memory location
    for (auto reading : readingSet2->getAllReadings())
    {
        for (auto &dp : reading->getReadingData())
        {
            std::string dataPointName = dp->getName();
            DatapointValue dv = dp->getData();
            ASSERT_EQ(dataPointName, "degrees");
            ASSERT_EQ(dv.toDouble(), 200.65);
        }
    }

    // Confirm there is no error of double delete
    delete readingSet2;
}

TEST(READINGSET, DeepCopyCheckReadingFromVector)
{
    vector<Reading *> *readings1 = new vector<Reading *>;
    long integerValue = 100;
    DatapointValue dpv(integerValue);
    Datapoint *value = new Datapoint("kPa", dpv);
    Reading *in = new Reading("Pressure", value);
    readings1->push_back(in);

    ReadingSet *readingSet1 = new ReadingSet(readings1);
    ReadingSet *readingSet2 = new ReadingSet();
    readingSet2->copy(*readingSet1);

    delete readingSet1;

    // Fetch value after deleting readingSet1 to check readingSet2 is pointing to different memory location
    for (auto reading : readingSet2->getAllReadings())
    {
        for (auto &dp : reading->getReadingData())
        {
            std::string dataPointName = dp->getName();
            DatapointValue dv = dp->getData();
            ASSERT_EQ(dataPointName, "kPa");
            ASSERT_EQ(dv.toInt(), 100);
        }
    }
    // Confirm there is no error of double delete
    delete readingSet2;
}

TEST(READINGSET, DeepCopyCheckAppend)
{
    vector<Reading *> *readings1 = new vector<Reading *>;
    long integerValue = 100;
    DatapointValue dpv(integerValue);
    Datapoint *value = new Datapoint("kPa", dpv);
    Reading *in = new Reading("Pressure", value);
    readings1->push_back(in);
    ReadingSet *readingSet1 = new ReadingSet(readings1);

    vector<Reading *> *readings2 = new vector<Reading *>;
    long integerValue2 = 400;
    DatapointValue dpv2(integerValue2);
    Datapoint *value2 = new Datapoint("kPa", dpv2);
    Reading *in2 = new Reading("Pressure", value2);
    readings2->push_back(in2);
    ReadingSet *readingSet2 = new ReadingSet(readings2);

    readingSet2->copy(*readingSet1);

    int size = readingSet2->getAllReadings().size();
    ASSERT_EQ(size, 2);
}

TEST(READINGSET, DeepCopyCheckAddress)
{
    vector<Reading *> *readings1 = new vector<Reading *>;
    long integerValue = 100;
    DatapointValue dpv(integerValue);
    Datapoint *value = new Datapoint("kPa", dpv);
    Reading *in = new Reading("Pressure", value);
    readings1->push_back(in);

    ReadingSet *readingSet1 = new ReadingSet(readings1);
    ReadingSet *readingSet2 = new ReadingSet();
    readingSet2->copy(*readingSet1);

    auto r1 = readingSet1->getAllReadings();
    auto dp1 = r1[0]->getReadingData();

    auto r2 = readingSet2->getAllReadings();
    auto dp2 = r2[0]->getReadingData();

    ASSERT_NE(dp1, dp2);
}

/*
 * unit tests - FOGL-8750 : ReadingSet Circular Buffer
 *
 * Copyright (c) 2024 Dianomic Systems, Inc.
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <gtest/gtest.h>
#include <readingset_circularbuffer.h>
#include <exception>

using namespace std;

TEST(TESTCircularBuffer, TestMaxLimitOfBuffer)
{
	ReadingSetCircularBuffer buffer;
    //First ReadingSet
    vector<Reading *> *readings1 = new vector<Reading *>;
    long dpVal1 = 30;
    DatapointValue dpv1(dpVal1);
    readings1->emplace_back(new Reading("R1", new Datapoint("DP1", dpv1)));
    ReadingSet* rs1 = new  ReadingSet(readings1);
    buffer.insert(rs1);
    delete readings1;

    //Second ReadingSet
    long dpVal2 = 50;
    DatapointValue dpv2(dpVal2);
    vector<Reading *> *readings2 = new vector<Reading *>;
    readings2->emplace_back(new Reading("R2", new Datapoint("DP2", dpv2)));
    ReadingSet* rs2 = new  ReadingSet(readings2);
    buffer.insert(rs2);
    delete readings2;

    //Third ReadingSet
    long dpVal3 = 40;
    DatapointValue dpv3(dpVal3);
    vector<Reading *> *readings3 = new vector<Reading *>;
    readings3->emplace_back(new Reading("R3", new Datapoint("DP3", dpv3)));
    ReadingSet* rs3 = new  ReadingSet(readings3);
    buffer.insert(rs3);
    delete readings3;

    //Fourth ReadingSet
    long dpVal4 = 45;
    DatapointValue dpv4(dpVal4);
    vector<Reading *> *readings4 = new vector<Reading *>;
    readings4->emplace_back(new Reading("R4", new Datapoint("DP4", dpv4)));
    ReadingSet* rs4 = new  ReadingSet(readings4);
    buffer.insert(rs4);
    delete readings4;

    //Fifth ReadingSet
    long dpVal5 = 86;
    DatapointValue dpv5(dpVal5);
    vector<Reading *> *readings5 = new vector<Reading *>;
    readings5->emplace_back(new Reading("R5", new Datapoint("DP5", dpv5)));
    ReadingSet* rs5 = new  ReadingSet(readings5);
    buffer.insert(rs5);
    delete readings5;

    //Sixth ReadingSet
    long dpVal6 = 75;
    DatapointValue dpv6(dpVal6);
    vector<Reading *> *readings6 = new vector<Reading *>;
    readings6->emplace_back(new Reading("R6", new Datapoint("DP6", dpv6)));
    ReadingSet* rs6 = new  ReadingSet(readings6);
    buffer.insert(rs6);
    delete readings6;

    //Seventh ReadingSet
    long dpVal7 = 49;
    DatapointValue dpv7(dpVal4);
    vector<Reading *> *readings7 = new vector<Reading *>;
    readings7->emplace_back(new Reading("R7", new Datapoint("DP7", dpv7)));
    ReadingSet* rs7 = new  ReadingSet(readings7);
    buffer.insert(rs7);
    delete readings7;

    //Eighth ReadingSet
    long dpVal8 = 15;
    DatapointValue dpv8(dpVal8);
    vector<Reading *> *readings8 = new vector<Reading *>;
    readings8->emplace_back(new Reading("R8", new Datapoint("DP8", dpv8)));
    ReadingSet* rs8 = new  ReadingSet(readings8);
    buffer.insert(rs8);
    delete readings8;

    //Ninth ReadingSet
    long dpVal9 = 23;
    DatapointValue dpv9(dpVal9);
    vector<Reading *> *readings9 = new vector<Reading *>;
    readings9->emplace_back(new Reading("R9", new Datapoint("DP9", dpv4)));
    ReadingSet* rs9 = new  ReadingSet(readings9);
    buffer.insert(rs9);
    delete readings9;

    //Tenth ReadingSet
    long dpVal10 = 38;
    DatapointValue dpv10(dpVal10);
    vector<Reading *> *readings10 = new vector<Reading *>;
    readings10->emplace_back(new Reading("R10", new Datapoint("DP10", dpv4)));
    ReadingSet* rs10 = new  ReadingSet(readings10);
    buffer.insert(rs10);
    delete readings10;
    ASSERT_EQ(buffer.extract(false).size(),10); // MaxLimit for buffer is reached
    
    //Eleventh ReadingSet
    long dpVal11 = 47;
    DatapointValue dpv11(dpVal11);
    vector<Reading *> *readings11 = new vector<Reading *>;
    readings11->emplace_back(new Reading("R4", new Datapoint("DP11", dpv11)));
    ReadingSet* rs11 = new  ReadingSet(readings11);
    buffer.insert(rs11);
    delete readings11;
    
    ASSERT_EQ(buffer.extract(false).size(),1); // Buffer size can't exceed the default MaxLimit
}



TEST(TESTCircularBuffer, TestCustomSizeBuffer)
{
	ReadingSetCircularBuffer buffer(5);
    //First ReadingSet
    vector<Reading *> *readings1 = new vector<Reading *>;
    long dpVal1 = 30;
    DatapointValue dpv1(dpVal1);
    readings1->emplace_back(new Reading("R1", new Datapoint("DP1", dpv1)));
    ReadingSet* rs1 = new  ReadingSet(readings1);
    buffer.insert(rs1);
    delete readings1;
    ASSERT_EQ(buffer.extract().size(),1);

    //Second ReadingSet
    long dpVal2 = 50;
    DatapointValue dpv2(dpVal2);
    vector<Reading *> *readings2 = new vector<Reading *>;
    readings2->emplace_back(new Reading("R2", new Datapoint("DP2", dpv2)));
    ReadingSet* rs2 = new  ReadingSet(readings2);
    buffer.insert(rs2);
    delete readings2;

    //Third ReadingSet
    long dpVal3 = 40;
    DatapointValue dpv3(dpVal3);
    vector<Reading *> *readings3 = new vector<Reading *>;
    readings3->emplace_back(new Reading("R3", new Datapoint("DP3", dpv3)));
    ReadingSet* rs3 = new  ReadingSet(readings3);
    buffer.insert(rs3);
    delete readings3;

    //Fourth ReadingSet
    long dpVal4 = 45;
    DatapointValue dpv4(dpVal4);
    vector<Reading *> *readings4 = new vector<Reading *>;
    readings4->emplace_back(new Reading("R4", new Datapoint("DP4", dpv4)));
    ReadingSet* rs4 = new  ReadingSet(readings4);
    buffer.insert(rs4);
    delete readings4;

    //Fifth ReadingSet
    long dpVal5 = 86;
    DatapointValue dpv5(dpVal5);
    vector<Reading *> *readings5 = new vector<Reading *>;
    readings5->emplace_back(new Reading("R5", new Datapoint("DP5", dpv5)));
    ReadingSet* rs5 = new  ReadingSet(readings5);
    buffer.insert(rs5);
    delete readings5;
    ASSERT_EQ(buffer.extract(false).size(),4); // Remaining item in buffer

    //Sixth ReadingSet
    long dpVal6 = 75;
    DatapointValue dpv6(dpVal6);
    vector<Reading *> *readings6 = new vector<Reading *>;
    readings6->emplace_back(new Reading("R6", new Datapoint("DP6", dpv6)));
    ReadingSet* rs6 = new  ReadingSet(readings6);
    buffer.insert(rs6);
    delete readings6;
    ASSERT_EQ(buffer.extract(false).size(),1); // Buffer size can't exceed the default MaxLimit
}


TEST(TESTCircularBuffer, TestExtactFromEmptyBuffer)
{
	ReadingSetCircularBuffer buffer;
    ASSERT_EQ(buffer.extract(false).size(),0); // Buffer size zero in case of extract from an empty buffer

}

TEST(TESTCircularBuffer, TestHeadAndTailMarkerAdjustment)
{
	ReadingSetCircularBuffer buffer(3);
    //First ReadingSet
    vector<Reading *> *readings1 = new vector<Reading *>;
    long dpVal1 = 30;
    DatapointValue dpv1(dpVal1);
    readings1->emplace_back(new Reading("R1", new Datapoint("DP1", dpv1)));
    ReadingSet* rs1 = new  ReadingSet(readings1);
    buffer.insert(rs1);
    std::vector<std::shared_ptr<ReadingSet>> buff1 = buffer.extract();
    ASSERT_EQ(buff1.size(),1);
    ASSERT_EQ(buff1[0]->getAllReadings()[0]->getAssetName(), "R1");
    ASSERT_EQ(buff1[0]->getAllReadings()[0]->getDatapointsJSON(), readings1->at(0)->getDatapointsJSON());
    delete readings1;


    //Second ReadingSet
    long dpVal2 = 50;
    DatapointValue dpv2(dpVal2);
    vector<Reading *> *readings2 = new vector<Reading *>;
    readings2->emplace_back(new Reading("R2", new Datapoint("DP2", dpv2)));
    ReadingSet* rs2 = new  ReadingSet(readings2);
    buffer.insert(rs2);
    
    std::vector<std::shared_ptr<ReadingSet>> buff2 = buffer.extract();
    ASSERT_EQ(buff2.size(),1);
    ASSERT_EQ(buff2[0]->getAllReadings()[0]->getAssetName(), "R2");
    ASSERT_EQ(buff2[0]->getAllReadings()[0]->getDatapointsJSON(), readings2->at(0)->getDatapointsJSON());
    delete readings2;

    //Third ReadingSet
    long dpVal3 = 40;
    DatapointValue dpv3(dpVal3);
    vector<Reading *> *readings3 = new vector<Reading *>;
    readings3->emplace_back(new Reading("R3", new Datapoint("DP3", dpv3)));
    ReadingSet* rs3 = new  ReadingSet(readings3);
    buffer.insert(rs3);
    
    std::vector<std::shared_ptr<ReadingSet>> buff3 = buffer.extract();
    ASSERT_EQ(buff3.size(),1);
    ASSERT_EQ(buff3[0]->getAllReadings()[0]->getAssetName(), "R3"); //Buffer is Full
    ASSERT_EQ(buff3[0]->getAllReadings()[0]->getDatapointsJSON(), readings3->at(0)->getDatapointsJSON());
    delete readings3;

    //Fourth ReadingSet
    long dpVal4 = 45;
    DatapointValue dpv4(dpVal4);
    vector<Reading *> *readings4 = new vector<Reading *>;
    readings4->emplace_back(new Reading("R4", new Datapoint("DP4", dpv4)));
    ReadingSet* rs4 = new  ReadingSet(readings4);
    buffer.insert(rs4);
    
    std::vector<std::shared_ptr<ReadingSet>> buff4 = buffer.extract();
    ASSERT_EQ(buff4.size(),1);
    // m_head and m_tail pointer set correctly to fetch the reading which came after buffer is full
    ASSERT_EQ(buff4[0]->getAllReadings()[0]->getAssetName(), "R4"); 
    ASSERT_EQ(buff4[0]->getAllReadings()[0]->getDatapointsJSON(), readings4->at(0)->getDatapointsJSON());
    delete readings4;

}

TEST(TESTCircularBuffer, TestCustomSizeBufferLessThanOne)
{
    ReadingSetCircularBuffer buffer(0);

    //First ReadingSet
    vector<Reading *> *readings1 = new vector<Reading *>;
    long dpVal1 = 30;
    DatapointValue dpv1(dpVal1);
    readings1->emplace_back(new Reading("R1", new Datapoint("DP1", dpv1)));
    ReadingSet* rs1 = new  ReadingSet(readings1);
    buffer.insert(rs1);

    std::vector<std::shared_ptr<ReadingSet>> buff1 = buffer.extract();
    ASSERT_EQ(buff1.size(),1);
    ASSERT_EQ(buff1[0]->getAllReadings()[0]->getAssetName(), "R1");
    ASSERT_EQ(buff1[0]->getAllReadings()[0]->getDatapointsJSON(), readings1->at(0)->getDatapointsJSON());
    delete readings1;

    //Second ReadingSet
    long dpVal2 = 50;
    DatapointValue dpv2(dpVal2);
    vector<Reading *> *readings2 = new vector<Reading *>;
    readings2->emplace_back(new Reading("R2", new Datapoint("DP2", dpv2)));
    ReadingSet* rs2 = new  ReadingSet(readings2);
    buffer.insert(rs2);

    std::vector<std::shared_ptr<ReadingSet>> buff2 = buffer.extract();
    ASSERT_EQ(buff2.size(),1);
    ASSERT_EQ(buff2[0]->getAllReadings()[0]->getAssetName(), "R2");
    ASSERT_EQ(buff2[0]->getAllReadings()[0]->getDatapointsJSON(), readings2->at(0)->getDatapointsJSON());
    delete readings2;

}


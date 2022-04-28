#include <gtest/gtest.h>
#include <reading.h>
#include <reading_set.h>
#include <rapidjson/document.h>
#include <string.h>
#include <string>
#include <logger.h>

using namespace std;
using namespace rapidjson;

TEST(ImageEncodingTest, ImageRoundTrip64)
{
	uint16_t *data = (uint16_t *)malloc(64 * 64 * 2);
	uint16_t *ptr = data;
	for (int i = 0; i < 64; i++)
		for (int j = 0; j < 64; j++)
			*ptr++ = 0 + i + j;
	DPImage  *image = new DPImage(64, 64, 16, data);
	DatapointValue img(image);
	Reading reading("test", new Datapoint("image", img));
	string json = reading.toJSON();
	Document doc;
	doc.Parse(json.c_str());
	JSONReading decoded(doc);
	Datapoint *dp = decoded.getDatapoint("image");
	DPImage *image2 = dp->getData().getImage();
	ASSERT_EQ(image->getWidth(), image2->getWidth());
	ASSERT_EQ(image->getHeight(), image2->getHeight());
	ASSERT_EQ(image->getDepth(), image2->getDepth());
	uint16_t *ptr2 = (uint16_t *)image2->getData();
	ptr = data;
	for (int i = 0; i < 64; i++)
		for (int j = 0; j < 64; j++)
		{
			if (*ptr != *ptr2)
			{
				printf("Differ at %d, %d", i, j);
			}
			ASSERT_EQ(*ptr, *ptr2);
			ptr++;
			ptr2++;
		}
}

TEST(ImageEncodingTest, ImageRoundTrip65)
{
	uint16_t *data = (uint16_t *)malloc(64 * 65 * 2);
	uint16_t *ptr = data;
	for (int i = 0; i < 64; i++)
		for (int j = 0; j < 65; j++)
			*ptr++ = 100 + i + j;
	DPImage  *image = new DPImage(64, 65, 16, data);
	DatapointValue img(image);
	Reading reading("test", new Datapoint("image", img));
	string json = reading.toJSON();
	Document doc;
	doc.Parse(json.c_str());
	JSONReading decoded(doc);
	Datapoint *dp = decoded.getDatapoint("image");
	DPImage *image2 = dp->getData().getImage();
	ASSERT_EQ(image->getWidth(), image2->getWidth());
	ASSERT_EQ(image->getHeight(), image2->getHeight());
	ASSERT_EQ(image->getDepth(), image2->getDepth());
	uint16_t *ptr2 = (uint16_t *)image2->getData();
	ptr = data;
	for (int i = 0; i < 64; i++)
		for (int j = 0; j < 65; j++)
		{
			if (*ptr != *ptr2)
			{
				printf("Differ at %d, %d", i, j);
			}
			ASSERT_EQ(*ptr, *ptr2);
			ptr++;
			ptr2++;
		}
}

TEST(ImageEncodingTest, ImageRoundTrip66)
{
	uint16_t *data = (uint16_t *)malloc(64 * 66 * 2);
	uint16_t *ptr = data;
	for (int i = 0; i < 64; i++)
		for (int j = 0; j < 66; j++)
			*ptr++ = 200 + i + j;
	DPImage  *image = new DPImage(64, 66, 16, data);
	DatapointValue img(image);
	Reading reading("test", new Datapoint("image", img));
	string json = reading.toJSON();
	Document doc;
	doc.Parse(json.c_str());
	JSONReading decoded(doc);
	Datapoint *dp = decoded.getDatapoint("image");
	DPImage *image2 = dp->getData().getImage();
	ASSERT_EQ(image->getWidth(), image2->getWidth());
	ASSERT_EQ(image->getHeight(), image2->getHeight());
	ASSERT_EQ(image->getDepth(), image2->getDepth());
	uint16_t *ptr2 = (uint16_t *)image2->getData();
	ptr = data;
	for (int i = 0; i < 64; i++)
		for (int j = 0; j < 66; j++)
		{
			if (*ptr != *ptr2)
			{
				printf("Differ at %d, %d", i, j);
			}
			ASSERT_EQ(*ptr, *ptr2);
			ptr++;
			ptr2++;
		}
}

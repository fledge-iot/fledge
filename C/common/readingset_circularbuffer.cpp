/*
 * Fledge ReadingSet Circular Buffer.
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */
#include <readingset_circularbuffer.h>
#include <logger.h>


using namespace std;
using namespace rapidjson;

/**
 * Construct an empty reading set circular buffer
 */
ReadingSetCircularBuffer::ReadingSetCircularBuffer(unsigned long maxBufferSize) : m_maxBufferSize(maxBufferSize), m_head(0), m_tail(0)
{
}

/**
 * Destructor for a result set
 */
ReadingSetCircularBuffer::~ReadingSetCircularBuffer()
{
	/* Delete the readings */
	m_circularBuffer.clear();
}

void ReadingSetCircularBuffer::insert(ReadingSet& readings)
{
	appendReadingSet(readings.getAllReadings());
}

void ReadingSetCircularBuffer::insert(ReadingSet* readings)
{
	appendReadingSet(readings->getAllReadings());
}

void ReadingSetCircularBuffer::appendReadingSet(const std::vector<Reading *>& readings)
{
	lock_guard<mutex> guard(m_mutex);
	//Check if there is space available to insert a new ReadingSet
	if (m_circularBuffer.size() == m_maxBufferSize)
	{
		Logger::getLogger()->info("ReadingSetCircularBuffer buffer is full, removing first element");
		// Make space for new ReadingSet and adjust m_head marker
		m_circularBuffer.erase(m_circularBuffer.begin() + m_head);

		m_tail = (m_tail < m_maxBufferSize && (m_tail + 1) != m_maxBufferSize) ? (m_tail + 1) : 0;
	}	

	std::vector<Reading *> *newReadings = new std::vector<Reading *>;
	
	// Iterate over all the readings in ReadingSet
	for (auto const &reading : readings)
	{
		std::string assetName = reading->getAssetName();
		std::vector<Datapoint *> dataPoints;

		try
		{
			// Iterate over all the datapoints associated with one reading
			for (auto const &dp : reading->getReadingData())
			{
				std::string dataPointName  = dp->getName();
				DatapointValue dv = dp->getData();
				dataPoints.emplace_back(new Datapoint(dataPointName, dv));
				
			}
		}
		// Catch exception while copying datapoints
		catch(std::bad_alloc& ex)
		{
			Logger::getLogger()->error("Insufficient memory, failed while copying dataPoints from ReadingSet, %s ", ex.what());
			for (auto const &dp : dataPoints)
			{
				delete dp;
			}
			dataPoints.clear();
			throw;
		}
		catch (std::exception& ex)
		{
			Logger::getLogger()->error("Unknown exception, failed while copying datapoint from ReadingSet, %s ", ex.what());
			for (auto const &dp : dataPoints)
			{
				delete dp;
			}
			dataPoints.clear();
			throw;
		}
		Reading *in = new Reading(assetName, dataPoints);
		newReadings->emplace_back(in);
		
	}
	// Insert ReadingSet into buffer and adjust m_tail marker
	m_circularBuffer.push_back(std::make_shared<ReadingSet>(newReadings));
	m_tail = (m_tail < m_maxBufferSize && (m_tail + 1) != m_maxBufferSize) ? (m_tail + 1) : 0;
	
}

std::vector<std::shared_ptr<ReadingSet>> ReadingSetCircularBuffer::extract(bool isExtractSingleElement)
{
	lock_guard<mutex> guard(m_mutex);
	bool isEmpty = m_circularBuffer.empty();
	
	if (isEmpty)
		 Logger::getLogger()->warn("ReadingSet circular buffer is empty");

	if (!isExtractSingleElement || isEmpty)
		return m_circularBuffer;
	
	std::vector<std::shared_ptr<ReadingSet>> bufferedItem;
	bufferedItem.emplace_back(m_circularBuffer[m_head]);
	if (m_head < m_circularBuffer.size()-1)
		m_head = (m_head < m_maxBufferSize && (m_head + 1) != m_maxBufferSize) ? (m_head + 1) : 0;
	return  bufferedItem;

}

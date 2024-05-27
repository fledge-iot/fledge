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
ReadingSetCircularBuffer::ReadingSetCircularBuffer(unsigned long maxBufferSize) : m_maxBufferSize(maxBufferSize), m_head(0), m_tail(-1)
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

/**
 * Insert a ReadingSet into circular buffer
 *
 * @param readings		Reference for ReadingSet to be inserted into circular buffer
 */
void ReadingSetCircularBuffer::insert(ReadingSet& readings)
{
	appendReadingSet(readings.getAllReadings());
}

/**
 * Insert a ReadingSet into circular buffer
 *
 * @param readings		Pointer for ReadingSet to be inserted into circular buffer
 */
void ReadingSetCircularBuffer::insert(ReadingSet* readings)
{
	appendReadingSet(readings->getAllReadings());
}

/**
 * Internal implementation for inserting ReadingSet into the circular buffer
 *
 * @param readings		appends ReadingSet into the circular buffer
 */
void ReadingSetCircularBuffer::appendReadingSet(const std::vector<Reading *>& readings)
{
	lock_guard<mutex> guard(m_mutex);
	//Check if there is space available to insert a new ReadingSet
	if (isBufferFull())
	{
		Logger::getLogger()->info("ReadingSetCircularBuffer buffer is full, removing first element");
		// Make space for new ReadingSet and adjust m_head marker
		m_circularBuffer.erase(m_circularBuffer.begin() + 0);
		m_tail--;
		if (m_head > m_tail)
             m_head--;
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
		catch(const std::bad_alloc& ex)
		{
			Logger::getLogger()->error("Insufficient memory, failed while copying dataPoints from ReadingSet, %s ", ex.what());
			for (auto const &dp : dataPoints)
			{
				delete dp;
			}
			dataPoints.clear();
			throw;
		}
		catch (const std::exception& ex)
		{
			Logger::getLogger()->error("failed while copying datapoint from ReadingSet, %s", ex.what());
			for (auto const &dp : dataPoints)
			{
				delete dp;
			}
			dataPoints.clear();
			throw;
		}
		catch (...)
		{
			Logger::getLogger()->error("Unknown exception, failed while copying datapoint from ReadingSet");
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
	m_tail++;
	
}

/**
 * Extract the ReadingSet from circular buffer
 *
 * @param isExtractSingleElement True to extract single ReadingSet otherwise for extract entire buffer 
 * @return		Return a vector of shared pointer to ReadingSet
 */
std::vector<std::shared_ptr<ReadingSet>> ReadingSetCircularBuffer::extract(bool isExtractSingleElement)
{
	lock_guard<mutex> guard(m_mutex);
	bool isEmpty = isBufferEmpty();
	
	if (isEmpty)
		 Logger::getLogger()->info("ReadingSet circular buffer is empty");

	if (!isExtractSingleElement || isEmpty)
		return m_circularBuffer;
	
	std::vector<std::shared_ptr<ReadingSet>> bufferedItem;
	bufferedItem.emplace_back(m_circularBuffer[m_head]);
	
	if (m_head  < m_circularBuffer.size())
		m_head++;
	return  bufferedItem;

}

/**
 * Check if circular buffer is empty
 *
 * @return	Return true if circular buffer is empty otherwise false
 *
 */
bool ReadingSetCircularBuffer::isBufferEmpty()
{
	return m_circularBuffer.empty();
}

/**
 * Check if circular buffer is full
 *
 * @return	Return true if circular buffer is full otherwise false
 *
 */
bool ReadingSetCircularBuffer::isBufferFull()
{
	return (m_circularBuffer.size() == m_maxBufferSize);
}


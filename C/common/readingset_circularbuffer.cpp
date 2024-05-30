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
 *
 * @param maxBufferSize Maximum size of the ReadingSet circular buffer. It should be atleast one.
 */
ReadingSetCircularBuffer::ReadingSetCircularBuffer(unsigned long maxBufferSize)
{
	if ( maxBufferSize <= 0)
	{
		maxBufferSize = 1;
		Logger::getLogger()->warn("Minimum size of ReadingSetCircularBuffer cannot be less than one, setting buffer size to 1");
	}
	m_maxBufferSize = maxBufferSize;
	m_nextReadIndex = 0;
}

/**
 * Destructor for a result set
 */
ReadingSetCircularBuffer::~ReadingSetCircularBuffer()
{
	lock_guard<mutex> guard(m_mutex);
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
	bool isBufferFull = (m_circularBuffer.size() == m_maxBufferSize);

	//Check if there is space available to insert a new ReadingSet
	if (isBufferFull)
	{
		Logger::getLogger()->info("ReadingSetCircularBuffer buffer is full, removing first element");
		// Make space for new ReadingSet and adjust m_nextReadIndex
		m_circularBuffer.erase(m_circularBuffer.begin() + 0);
		m_nextReadIndex--;
	}	

	std::vector<Reading *> *newReadings = new std::vector<Reading *>;
	
	// Iterate over all the readings in ReadingSet
	for (auto const &reading : readings)
	{
		newReadings->emplace_back(new Reading(*reading));
	}
	// Insert ReadingSet into buffer
	m_circularBuffer.push_back(std::make_shared<ReadingSet>(newReadings));
	
}

/**
 * Fetch the vector of ReadingSet from circular buffer
 *
 * @param isExtractSingleElement True to extract single ReadingSet otherwise for extract entire buffer 
 * @return		Return a vector of shared pointer to ReadingSet
 */
std::vector<std::shared_ptr<ReadingSet>> ReadingSetCircularBuffer::extract(bool isExtractSingleElement)
{
	
    lock_guard<mutex> guard(m_mutex);
    bool isNoDataToRead = m_circularBuffer.empty() || (m_nextReadIndex == m_circularBuffer.size());
    std::vector<std::shared_ptr<ReadingSet>> bufferedItem;
    // Check for empty buffer
    if (isNoDataToRead)
    {
	Logger::getLogger()->info("There is no more data to read in ReadingSet circualr buffer");
	return  bufferedItem;
    }

    // Return single item from buffer
    if (isExtractSingleElement)
    {
        bufferedItem.emplace_back(m_circularBuffer[m_nextReadIndex]);
        m_nextReadIndex++;
        return  bufferedItem;
    }

    // Return Entire buffer
    if(m_nextReadIndex == 0)
    {
        m_nextReadIndex = m_circularBuffer.size();
        return m_circularBuffer;
    }
    // Send remaining items in the buffer
    for (int i = m_nextReadIndex; i <  m_circularBuffer.size(); i ++)
        bufferedItem.emplace_back(m_circularBuffer[i]);

    m_nextReadIndex =  m_circularBuffer.size();
	return bufferedItem;
}

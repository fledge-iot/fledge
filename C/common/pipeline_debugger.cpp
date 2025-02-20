/*
 * Fledge pipeline debugger class
 *
 * Copyright (c) 2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <pipeline_debugger.h>

using namespace std;

/**
 * Constructor for the pipeline element debugger
 */
PipelineDebugger::PipelineDebugger() : m_buffer(NULL)
{
}

/**
 * Destructor for the pipeline element debugger
 */
PipelineDebugger::~PipelineDebugger()
{
	if (m_buffer)
		delete m_buffer;
}

/**
 * Process a reading set as it flows through the pipeline.
 * The main purpose here is to buffer the readings in the circular
 * buffer in order to allow later examination of the data.
 *
 * @param readings		The reading set flowing into the pipeline element
 * @return DebuggerActions	Action signal to the pipeline
 */
PipelineDebugger::DebuggerActions PipelineDebugger::process(ReadingSet *readings)
{
	lock_guard<mutex> guard(m_bufferMutex);
	if (!m_buffer)
		return NoAction;
	m_buffer->insert(readings->getAllReadings());
	return NoAction;
}

/**
 * Set the size of the circular buffer used to buffer
 * the data flowing in the pipeline
 *
 * @param size		The number of readings to buffer
 */
void PipelineDebugger::setBuffer(unsigned int size)
{
	lock_guard<mutex> guard(m_bufferMutex);
	if (m_buffer)
	{
		delete m_buffer;
	}
	m_buffer = new ReadingCircularBuffer(size);
}

/**
 * Remove the circular buffer of readings and stop the
 * process of storing future readings
 */
void PipelineDebugger::clearBuffer()
{
	lock_guard<mutex> guard(m_bufferMutex);
	if (m_buffer)
	{
		delete m_buffer;
		m_buffer = NULL;
	}
}

/**
 * Fetch the current contents of the circular buffer. A vector
 * of shared pointers is returned to alleviate the need to 
 * copy the readings.
 *
 * @return vector<shared_ptr<Reading> The readings that are returned
 */
std::vector<std::shared_ptr<Reading>> PipelineDebugger::fetchBuffer()
{
	vector<std::shared_ptr<Reading>> vec;
	lock_guard<mutex> guard(m_bufferMutex);
	if (m_buffer)
	{
		int extracted = m_buffer->extract(vec);
		Logger::getLogger()->debug("Debugger return %d readings", extracted);
	}
	return vec;
}

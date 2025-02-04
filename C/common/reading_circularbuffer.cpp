/*
 * Fledge reading circular buffer class
 *
 * Copyright (c) 2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <reading_circularbuffer.h>

using namespace std;

/**
 * Create a circular buffer of readings
 *
 * @param size	The numebr of items to retain oin the circular buffer
 */
ReadingCircularBuffer::ReadingCircularBuffer(unsigned int size) : m_size(size),
       	m_insert(0), m_entries(0)
{
	m_readings.resize(size, NULL);
}

/**
 * Destructor for the circular buffer
 */
ReadingCircularBuffer::~ReadingCircularBuffer()
{
	lock_guard<mutex> guard(m_mutex);
	for (int i = 0; i < m_entries; i++)
		m_readings[i] = NULL;
}

/**
 * Insert a single reading into the shared buffer
 *
 * @param reading	The reading to insert
 */
void ReadingCircularBuffer::insert(Reading *reading)
{
	lock_guard<mutex> guard(m_mutex);
	if (m_entries == m_size)
		m_readings[m_insert] = NULL;
	else
		m_entries++;
	shared_ptr<Reading> copy(new Reading(*reading));
	m_readings[m_insert] = copy;
	m_insert++;
	if (m_insert >= m_size)
		m_insert = 0;
}

/**
 * Insert a list of readings into the circular buffer
 *
 * @param readings	The set of readings to ingest
 */
void ReadingCircularBuffer::insert(const vector<Reading *>& readings)
{
	for (auto& reading : readings)
		insert(reading);
}

/**
 * Insert a list of readings into the circular buffer
 *
 * @param readings	The set of readings to ingest
 */
void ReadingCircularBuffer::insert(const vector<Reading *> *readings)
{
	for (auto& reading : *readings)
		insert(reading);
}

/**
 * Return the buffered data into a supplied vector
 *
 * @param vec	The vector to populate witht he shared pointers
 * @return int	The number of readings placed in the vector
 */
int ReadingCircularBuffer::extract(vector<shared_ptr<Reading>>& vec)
{
	int start = 0;
	lock_guard<mutex> guard(m_mutex);
	if (m_entries == m_size)
	{
		start = (m_insert + 1) % m_size;
	}
	for (int i = 0; i < m_entries; i++)
	{
		vec.push_back(m_readings[start % m_size]);
		start++;
	}
	return m_entries;
}

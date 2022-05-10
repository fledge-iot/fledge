/*
 * Fledge
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <databuffer.h>
#include <exception>
#include <stdexcept>
#include <stdlib.h>
#include <string.h>

using namespace std;
/**
 * Buffer constructor
 *
 * @param itemSize	The size of each item in the buffer
 * @param len		The length of the buffer, i.e. how many items can it hold
 */
DataBuffer::DataBuffer(size_t itemSize, size_t len) : m_itemSize(itemSize), m_len(len)
{
	m_data = calloc(len, itemSize);
	if (m_data == NULL)
		throw runtime_error("Insufficient memory to create buffer");
}

/**
 * DataBuffer destructor
 */
DataBuffer::~DataBuffer()
{
	if (m_data)
		free(m_data);
	m_data = NULL;
}

/**
 * DataBuffer copy constructor
 *
 * @param rhs	DataBuffer to copy
 */
DataBuffer::DataBuffer(const DataBuffer& rhs)
{
	m_itemSize = rhs.m_itemSize;
	m_len = rhs.m_len;
	m_data = calloc(m_len, m_itemSize);
	if (m_data)
		memcpy(m_data, rhs.m_data, m_itemSize * m_len);
	else
		throw runtime_error("Insufficient memory to copy databuffer");
}

/**
 * Populate the contents of a DataBuffer
 *
 * @param src		Source of the data
 * @param len		Number of bytes in the source to copy
 */
void DataBuffer::populate(void *src, int len)
{
	size_t toCopy = min((size_t)len, m_len * m_itemSize);
	memcpy(m_data, src, toCopy);
}

#ifndef _DATABUFFER_H
#define _DATABUFFER_H
/*
 * Fledge Databuffer type for datapoints
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <unistd.h>

/**
 * Buffer type for storage of arbitrary buffers of data within a datapoint.
 * A DataBuffer is essentially a 1 dimensional array of a memory primitive of
 * itemSize.
 */
class DataBuffer {
	public:
		DataBuffer(size_t itemSize, size_t len);
		DataBuffer(const DataBuffer& rhs);
		DataBuffer& operator=(const DataBuffer& rhs);
		~DataBuffer();
		void		populate(void *src, int len);
		/**
		 * Return the size of each item in the buffer
		 */
		size_t		getItemSize() { return m_itemSize; };
		/**
		 * Return the number of items in the buffer
		 */
		size_t		getItemCount() { return m_len; };
		/**
		 * Return a pointer to the raw data in the data buffer
		 */
		void		*getData() { return m_data; };
	protected:
		DataBuffer()	{};
		size_t		m_itemSize;
		size_t		m_len;
		void		*m_data;
};

#endif

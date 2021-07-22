#ifndef _DATABUFFER_H
#define _DATABUFFER_H
/*
 * Fledge
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <unistd.h>

/**
 * Buffer type for storage arbitrary buffers of data within a datapoint
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
		void		*getData() { return m_data; };
	protected:
		DataBuffer()	{};
		size_t		m_itemSize;
		size_t		m_len;
		void		*m_data;
};

#endif

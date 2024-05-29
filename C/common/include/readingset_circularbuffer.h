#ifndef _READINGSETCIRCULARBUFFER_H
#define _READINGSETCIRCULARBUFFER_H
/*
 * Fledge ReadingSet Circular Buffer.
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */
#include <reading_set.h>
#include <mutex>
#include <vector>
#include <memory>

/**
 * Reading set circular buffer class
 *
 * Reading set circular buffer is a data structure to hold ReadingSet
 * passed to a plugin.
 */
class ReadingSetCircularBuffer {
	public:
		ReadingSetCircularBuffer(unsigned long maxBufferSize=10);
		~ReadingSetCircularBuffer();

		void	insert(ReadingSet*);
		void	insert(ReadingSet&);
		std::vector<std::shared_ptr<ReadingSet>> extract(bool isExtractSingleElement=true);

	private:
		std::mutex	m_mutex;
		unsigned long	m_maxBufferSize;
		unsigned long	m_nextReadIndex;
		void appendReadingSet(const std::vector<Reading *>& readings);
		ReadingSetCircularBuffer (const ReadingSetCircularBuffer&) = delete;
		ReadingSetCircularBuffer&	operator=(const ReadingSetCircularBuffer&) = delete;
		std::vector<std::shared_ptr<ReadingSet>> m_circularBuffer;
};

#endif


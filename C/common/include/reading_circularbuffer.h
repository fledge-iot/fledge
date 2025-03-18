#ifndef _READING_CIRCULARBUFFER_H
#define _READING_CIRCULARBUFFER_H
/*
 * Fledge Reading Circular Buffer.
 *
 * Copyright (c) 2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <reading.h>
#include <mutex>
#include <vector>
#include <memory>

/**
 * A circular buffer of readings. The buffer size is set in the constructor,
 * when it fills the oldest reading will be overwritten by new readings being
 * appended.
 *
 * The user can extract the current state at any point in historic order.
 */
class ReadingCircularBuffer {
	public:
		ReadingCircularBuffer(unsigned int size);
		~ReadingCircularBuffer();
		void		insert(Reading *);
		void		insert(const std::vector<Reading *>& readings);
		void		insert(const std::vector<Reading *> *readings);
		int		extract(std::vector<std::shared_ptr<Reading>>& vec);
	private:
		unsigned int	m_size;
		std::mutex	m_mutex;
		std::vector<std::shared_ptr<Reading>>
				m_readings;
		unsigned int	m_insert;
		unsigned int	m_entries;

};
#endif

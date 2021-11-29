#ifndef _READINGSET_H
#define _READINGSET_H
/*
 * Fledge storage client.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <string>
#include <string.h>
#include <sstream>
#include <iostream>
#include <reading.h>
#include <rapidjson/document.h>
#include <vector>

/**
 * Reading set class
 *
 * A specialised container for a set of readings that allows
 * creation from a JSON document.
 */
class ReadingSet {
	public:
		ReadingSet();
		ReadingSet(const std::string& json);
		ReadingSet(std::vector<Reading *>* readings);
		~ReadingSet();

		unsigned long			getCount() const { return m_count; };
		const Reading			*operator[] (const unsigned int idx) {
							return m_readings[idx];
						};

		// Return the const reference of readings data
		const std::vector<Reading *>&	getAllReadings() const { return m_readings; };
		// Return the reference of readings
		std::vector<Reading *>*		getAllReadingsPtr() { return &m_readings; };

		// Return the reading id of the last  data element
		unsigned long			getLastId() const { return m_last_id; };
		unsigned long			getReadingId(uint32_t pos);
		void				append(ReadingSet *);
		void				append(ReadingSet&);
		void				append(const std::vector<Reading *> &);
		void				removeAll();
		void				clear();

	private:
		unsigned long			m_count;
		ReadingSet(const ReadingSet&);
		ReadingSet&			operator=(ReadingSet const &);
		std::vector<Reading *>		m_readings;
		// Id of last Reading element
		unsigned long			m_last_id;    // Id of the last Reading
};

/**
 * JSONReading class
 *
 * A specialised reading class that allows creation from a JSON document
 */
class JSONReading : public Reading {
	public:
		JSONReading(const rapidjson::Value& json);

		// Return the reading id
		unsigned long	getId() const { return m_id; };

	private:
                void escapeCharacter(std::string& stringToEvaluate, std::string pattern);
};

class ReadingSetException : public std::exception
{
	public:
		ReadingSetException(const char *what)
		{
			m_what = strdup(what);
		};
		~ReadingSetException()
		{
			if (m_what)
				free(m_what);
		};
		virtual const char *what() const throw()
		{
			return m_what;
		};
	private:
		char *m_what;
};
#endif


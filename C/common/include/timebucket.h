#ifndef _TIMEBUCKET_H
#define _TIMEBUCKET_H
/*
 * FogLAMP storage client.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>
#include <sstream>
#include <iostream>


/**
 * Timebucket clause in a selection of records
 */
class Timebucket {
	public:
		Timebucket(const std::string& column, unsigned int size,
			const std::string& format, const std::string& alias) :
				m_column(column), m_size(size), m_format(format), m_alias(alias) {};
		Timebucket(const std::string& column, unsigned int size,
			const std::string& format) :
				m_column(column), m_size(size), m_format(format), m_alias(column) {};
		~Timebucket() {};
		std::string	toJSON()
		{
		std::ostringstream json;

			json << "{ \"timestamp\" : \"" << m_column << "\", ";
			json << "\"size\" : \"" << m_size << "\", ";
			json << "\"format\" : \"" << m_format << "\", ";
			json << "\"alias\" : \"" << m_alias << "\" }";
			return json.str();
		}
	private:
		const std::string	m_column;
		unsigned int		m_size;
		const std::string	m_format;
		const std::string	m_alias;
};
#endif


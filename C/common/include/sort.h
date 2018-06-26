#ifndef _SORT_H
#define _SORT_H
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
 * Sort clause in a selection of records
 */
class Sort {
	public:
		Sort(const std::string& column) :
				m_column(column), m_reverse(false) {};
		Sort(const std::string& column, bool reverse) :
				m_column(column), m_reverse(reverse) {};
		~Sort() {};
		std::string	toJSON()
		{
		std::ostringstream json;

			json << "{ \"column\" : \"" << m_column << "\", ";
			json << "\"direction\" : \"" << (m_reverse ? "desc" : "asc") << "\" }";
			return json.str();
		}
	private:
		const std::string	m_column;
		bool			m_reverse;
};
#endif


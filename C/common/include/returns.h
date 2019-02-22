#ifndef _RETURNS_H
#define _RETURNS_H
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
 * Control a returned column
 */
class Returns {
	public:
		Returns(const std::string& column) :
				m_column(column) {};
		Returns(const std::string& column, const std::string& alias) :
				m_column(column), m_alias(alias) {};
		Returns(const std::string& column, const std::string& alias, const std::string& format) :
				m_column(column), m_alias(alias), m_format(format) {};
		~Returns() {};
		void		format(const std::string format)
		{
			m_format = format;
		}
		void		timezone(const std::string timezone)
		{
			m_timezone = timezone;
		}
		std::string	toJSON()
		{
		std::ostringstream json;

			if ((! m_alias.empty()) || (! m_format.empty()) || (! m_timezone.empty()))
			{
				json << "{ ";
				json << "\"column\" : \"" << m_column << "\"";
				if (! m_alias.empty())
					json << ", \"alias\" : \"" << m_alias << "\"";
				if (! m_format.empty())
					json << ", \"format\" : \"" << m_format << "\"";
				if (! m_timezone.empty())
					json << ", \"timezone\" : \"" << m_timezone << "\"";
				json << " }";
			}
			else
			{
				json << "\"" << m_column << "\"";
			}
			return json.str();
		}
	private:
		const std::string	m_column;
		const std::string	m_alias;
		std::string		m_format;
		std::string		m_timezone;
};
#endif

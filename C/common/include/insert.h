#ifndef _INSERT_H
#define _INSERT_H
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
#include <vector>
#include <resultset.h>
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/error/error.h"


/**
 * Class that defines data to be inserted or updated in a column within the table
 */
class InsertValue {
	public:
		InsertValue(const std::string& column, const std::string& value) :
				m_column(column)
		{
			m_value.str = (char *)malloc(value.length() + 1);
			strncpy(m_value.str, value.c_str(), value.length() + 1);
			m_type = STRING_COLUMN;
		};
		InsertValue(const std::string& column, const int value) :
				m_column(column)
		{
			m_value.ival = value;
			m_type = INT_COLUMN;
		};
		InsertValue(const std::string& column, const long value) :
				m_column(column)
		{
			m_value.ival = value;
			m_type = INT_COLUMN;
		};
		InsertValue(const std::string& column, const double value) :
				m_column(column)
		{
			m_value.fval = value;
			m_type = NUMBER_COLUMN;
		};
		InsertValue(const std::string& column, const rapidjson::Value& value) :
				m_column(column)
		{
			rapidjson::StringBuffer sb;
			rapidjson::Writer<rapidjson::StringBuffer> writer(sb);
			value.Accept(writer);
			std::string s = sb.GetString();
			m_value.str = (char *)malloc(s.length() + 1);
			strncpy(m_value.str, s.c_str(), s.length() + 1);
			m_type = JSON_COLUMN;
		};
		InsertValue(const InsertValue& rhs) : m_column(rhs.m_column)
		{
			m_type = rhs.m_type;
			switch (rhs.m_type)
			{
			case INT_COLUMN:
				m_value.ival = rhs.m_value.ival;
				break;
			case NUMBER_COLUMN:
				m_value.fval = rhs.m_value.fval;
				break;
			case STRING_COLUMN:
				m_value.str = strdup(rhs.m_value.str);
				break;
			case JSON_COLUMN:	// Internally stored a a string
				m_value.str = strdup(rhs.m_value.str);
				break;
			case BOOL_COLUMN:
				// TODO
				break;
			}
		}
		~InsertValue()
		{
			if (m_type == STRING_COLUMN || m_type == JSON_COLUMN)
			{
				free(m_value.str);
			}
		};
		const std::string	toJSON() const
		{
		std::ostringstream json;

			json << "\"" << m_column << "\" : ";
			switch (m_type)
			{
			case JSON_COLUMN:
				json << m_value.str;
				break;
			case BOOL_COLUMN:
				json << m_value.ival;
				break;
			case INT_COLUMN:
				json << m_value.ival;
				break;
			case NUMBER_COLUMN:
				json << m_value.fval;
				break;
			case STRING_COLUMN:
				json << "\"" << m_value.str << "\"";
				break;
			}
			return json.str();
		}
	private:
		InsertValue&		operator=(InsertValue const& rhs);
		const std::string	m_column;
		ColumnType		m_type;
		union {
			char	*str;
			long	ival;
			double	fval;
			}		m_value;
};

class InsertValues : public std::vector<InsertValue>
{
	public:
		const std::string	toJSON() const
		{
		std::ostringstream json;

			json << "{ ";
			for (std::vector<InsertValue>::const_iterator it = this->cbegin();
				 it != this->cend(); ++it)

			{
				json << it->toJSON();
				if (it + 1 != this->cend())
					json << ", ";
				else
					json << " ";
			}
			json << "}";
			return json.str();
		};
};
#endif


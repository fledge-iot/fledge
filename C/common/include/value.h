#ifndef _VALUE_H
#define _VALUE_H
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
 * A value in an update statement
 */
class UpdateValue {
	public:
		enum UpdateType {
			StringType,
			IntType,
			DoubleType,
			JSONType };
		UpdateValue(const std::string& column, const std::string& value) :
				m_column(column), m_value.str(value), m_type(UpdateValue::StringType) {};
		UpdateValue(const std::string& column, const int value) :
				m_column(column), m_value.ival(value), m_type(UpdateValue::IntType) {};
		UpdateValue(const std::string& column, const double value) :
				m_column(column), m_value.fval(value), m_type(UpdateValue::DoubleType) {};
		~UpdateValue() {};
		std::string	toJSON()
		{
		std::ostringstream json;

			json << "\"" << m_column << "\" : ";
			switch (m_type)
			{
			case UpdateValue::StringType:
				json << "\"" << m_value.str << "\"";
				break;
			case UpdateValue::IntType:
				json << m_value.ival;
				break;
			case UpdateValue::DoubleType:
				json << m_value.fval;
				break;
			case UpdateValue::JSONType:
				json << m_value.str;
				break;
			}
			return json.str();
		}
	private:
		const std::string	m_column;
		enum UpdateType		m_type;
		union {
			std::string	str;
			int		ival;
			double		fval;
		}			m_value;
};
#endif


#ifndef _EXPRESSION_H
#define _EXPRESSION_H
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


/**
 * Class that defines data to be inserted or updated in a column within the table
 */
class Expression {
	public:
		Expression(const std::string& column, const std::string& op, int value) :
			m_column(column), m_op(op), m_type(INT_COLUMN)
		{
			m_value.ival = value;
		};
		Expression(const std::string& column, const std::string& op, double value) :
			m_column(column), m_op(op), m_type(NUMBER_COLUMN)
		{
			m_value.fval = value;
		};
		const std::string	toJSON() const
		{
		std::ostringstream json;

			json << "{ \"column\" : \"" << m_column << "\", ";
			json << "\"operator\" : \"" << m_op << "\", ";
			json << "\"value\" : ";
			switch (m_type)
			{
			case JSON_COLUMN:
			case BOOL_COLUMN:
			case STRING_COLUMN:
				break;
			case INT_COLUMN:
				json << m_value.ival;
				break;
			case NUMBER_COLUMN:
				json << m_value.fval;
				break;
			}
			json << "}";
			return json.str();
		}
	private:
		const std::string	m_column;
		const std::string	m_op;
		ColumnType		m_type;
		union {
			long	ival;
			double	fval;
			}		m_value;
};

class ExpressionValues : public std::vector<Expression>
{
	public:
		const std::string	toJSON() const
		{
		std::ostringstream json;

			json << "[ ";
			for (std::vector<Expression>::const_iterator it = this->cbegin();
				 it != this->cend(); ++it)

			{
				json << it->toJSON();
				if (it + 1 != this->cend())
					json << ", ";
				else
					json << " ";
			}
			json << "]";
			return json.str();
		};
};
#endif

#ifndef _WHERE_H
#define _WHERE_H
/*
 * Fledge storage client.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <string>
#include <vector>

typedef enum Conditional {
	Older,
	Newer,
	Equals,
	NotEquals,
	GreaterThan,
	LessThan,
	In
} Condition;

/**
 * Where clause in a selection of records
 */
class Where {
	public:
		Where(const std::string& column, const Condition condition, const std::string& value) :
				m_column(column), m_condition(condition), m_and(0), m_or(0)
		{
			if (condition != In)
			{
				m_value = value;
			}
			else
			{
				m_in.push_back(value);
			}
		};
		Where(const std::string& column, const Condition condition, const std::string& value, Where *andCondition) :
				m_column(column), m_condition(condition), m_and(andCondition), m_or(0)
		{
			if (condition != In)
			{
				m_value = value;
			}
			else
			{
				m_in.push_back(value);
			}
		};
		~Where();
		void		andWhere(Where *condition) { m_and = condition; };
		void		orWhere(Where *condition) { m_or = condition; };
		void		addIn(const std::string& value)
		{
			if (m_condition == In)
			{
				m_in.push_back(value);
			}
		};
		const std::string	toJSON() const;
	private:
		Where(const Where&);
		Where&			operator=(Where const&);
		const std::string	m_column;
		const Condition		m_condition;
		std::string		m_value;
		Where			*m_and;
		Where			*m_or;
		std::vector<std::string>
					m_in;
};
#endif


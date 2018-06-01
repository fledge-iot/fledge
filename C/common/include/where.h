#ifndef _WHERE_H
#define _WHERE_H
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

typedef enum Conditional {
	Equals,
	NotEquals,
	GreaterThan,
	LessThan
} Condition;

/**
 * Where clause in a selection of records
 */
class Where {
	public:
		Where(const std::string& column, const Condition condition, const std::string& value) :
				m_column(column), m_condition(condition), m_value(value), m_and(0), m_or(0) {};
		Where(const std::string& column, const Condition condition, const std::string& value, Where *andCondition) :
				m_column(column), m_condition(condition), m_value(value), m_and(andCondition), m_or(0) {};
		~Where();
		void		andWhere(Where *condition) { m_and = condition; };
		void		orWhere(Where *condition) { m_or = condition; };
		const std::string	toJSON() const;
	private:
		Where(const Where&);
		Where&			operator=(Where const&);
		const std::string	m_column;
		const Condition		m_condition;
		const std::string	m_value;
		Where			*m_and;
		Where			*m_or;
};
#endif


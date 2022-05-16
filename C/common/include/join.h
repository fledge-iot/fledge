#ifndef _JOIN_H
#define _JOIN_H
/*
 * Fledge storage client.
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>

class Query;

/**
 * Join clause representation
 */
class Join {
	public:
		Join(const std::string& table, const std::string& on, Query *query) :
				m_table(table), m_column(on), m_on(on), m_query(query)
		{
		};
		Join(const std::string& table, const std::string& column, const std::string& on, Query *query) :
				m_table(table), m_column(column), m_on(on), m_query(query)
		{
		};
		~Join();
		const std::string	toJSON() const;
	private:
		Join(const Join&);
		Join&			operator=(Join const&);
		const std::string	m_table;
		const std::string	m_column;
		const std::string	m_on;
		Query			*m_query;
};
#endif


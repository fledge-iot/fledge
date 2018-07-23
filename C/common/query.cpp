/*
 * FogLAMP storage service client
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <query.h>
#include <sstream>
#include <iostream>

using namespace std;

/**
 * Construct a query with a simple where clause
 *
 * @param where	A pointer to the where condition
 */
Query::Query(Where *where) : m_where(where), m_limit(0), m_timebucket(0), m_distinct(false)
{
}

/**
 * Construct a query with a where clause and aggregate response
 *
 * @param aggregate	A ppointer to the aggregate operation to perform
 * @param where	A pointer to the where condition
 */
Query::Query(Aggregate *aggregate, Where *where) : m_where(where),
						   m_limit(0),
						   m_timebucket(0),
						   m_distinct(false)
{
	m_aggregates.push_back(aggregate);
}

/**
 * Construct a timebucket query with a simple where clause
 *
 * @param timebuck	A pointer to the timebucket definition
 * @param where	A pointer to the where condition
 */
Query::Query(Timebucket *timebucket, Where *where) : m_where(where),
						     m_limit(0),
						     m_timebucket(timebucket),
						     m_distinct(false)
{
}

/**
 * Construct a timebucket query with a simple where clause and a limit on
 * the rows to return
 *
 * @param timebuck	A pointer to the timebucket definition
 * @param where	A pointer to the where condition
 * @param limit	The number of rows to return
 */
Query::Query(Timebucket *timebucket, Where *where, unsigned int limit) : m_where(where),
									 m_limit(limit),
									 m_timebucket(timebucket),
									 m_distinct(false)
{
}

/**
 * Construct a query with a fixed set of returned values and a simple where clause
 *
 * @params returns	The set of rows to return
 * @params where	The where clause
 */
Query::Query(vector<Returns *> returns, Where *where) : m_where(where),
							m_limit(0),
							m_timebucket(0),
							m_distinct(false)
{
	for (auto it = returns.cbegin(); it != returns.cend(); ++it)
	{
		m_returns.push_back(*it);
	}
}

/**
 * Construct a query with a fixed set of returned values and a simple where clause
 * and return a limited set of rows
 *
 * @params returns	The set of rows to return
 * @params where	The where clause
 * @param limit		The numebr of rows to return
 */
Query::Query(vector<Returns *> returns, Where *where, unsigned int limit) : m_where(where),
									    m_limit(limit),
									    m_timebucket(0),
									    m_distinct(false)
{
	for (auto it = returns.cbegin(); it != returns.cend(); ++it)
	{
		m_returns.push_back(*it);
	}
}

/**
 * Construct a simple query to return certain columns from a table
 *
 * @param returns	The rows to return
 */
Query::Query(vector<Returns *> returns) : m_where(0),
					  m_limit(0),
					  m_timebucket(0),
					  m_distinct(false)
{
	for (auto it = returns.cbegin(); it != returns.cend(); ++it)
	{
		m_returns.push_back(*it);
	}
}

/**
 * Construct a simple query to return a certain column from a table
 *
 * @param returns	The rows to return
 */
Query::Query(Returns *returns) : m_where(0),
				 m_limit(0),
				 m_timebucket(0),
				 m_distinct(false)
{
		m_returns.push_back(returns);
}

/**
 * Destructor for a query object
 */
Query::~Query()
{
	delete m_where;
	for (auto it = m_aggregates.cbegin(); it != m_aggregates.cend(); ++it)
	{
		delete *it;
	}
	for (auto it = m_sort.cbegin(); it != m_sort.cend(); ++it)
	{
		delete *it;
	}
	for (auto it = m_returns.cbegin(); it != m_returns.cend(); ++it)
	{
		delete *it;
	}
	if (m_timebucket)
	{
		delete m_timebucket;
	}
}

/**
 * Add a aggregate operation to an existing query object
 *
 * @param aggregate	The aggregate operation to add
 */
void Query::aggregate(Aggregate *aggregate)
{
	m_aggregates.push_back(aggregate);
}

/**
 * Add a sort operation to an existing query
 *
 * @param sort	The sort operation to add
 */
void Query::sort(Sort *sort)
{
	m_sort.push_back(sort);
}

/**
 * Add a group operation to a query
 *
 * @param column	The column to group by
 */
void Query::group(const string& column)
{
	m_group = column;
}

/**
 * Limit the numebr of rows returned by the query
 *
 * @param limit	The number of rows to limit the return to
 */
void Query::limit(unsigned int limit)
{
	m_limit = limit;
}

/**
 * Add a timebucket operation to an existing query
 *
 * @param timebucket	The timebucket operation to add to the query
 */
void Query::timebucket(Timebucket *timebucket)
{
	m_timebucket = timebucket;
}

/**
 * Limit the query to return just a single column
 *
 * @param returns	The column to return
 */
void Query::returns(Returns *returns)
{
	m_returns.push_back(returns);
}

/**
 * Limit the columns returned by the query
 *
 * @param returns	The columns to return
 */
void Query::returns(vector<Returns *> returns)
{
	for (auto it = returns.cbegin(); it != returns.cend(); ++it)
	{
		m_returns.push_back(*it);
	}
}

/**
 * Add a distinct value modifier to the query
 */
void Query::distinct()
{
	m_distinct = true;
}

/**
 * Return the JSON payload for a where clause
 */
const string Query::toJSON() const
{
ostringstream   json;
bool 		first = true;

	json << "{ ";
	if (m_where)
	{
		if (! first)
			json << ", ";
		json << "\"where\" : " << m_where->toJSON();
		first = false;
	}
	switch (m_aggregates.size())
	{
	case 0:
		break;
	case 1:
		if (! first)
			json << ", ";
		json << "\"aggregate\" : " << m_aggregates.front()->toJSON();
		first = false;
		break;
	default:
		if (! first)
			json << ", ";
		json << "\"aggregate\" : [ ";
		for (auto it = m_aggregates.cbegin(); it != m_aggregates.cend(); ++it)
		{
			if (it != m_aggregates.cbegin())
				json << ", ";
			json << (*it)->toJSON();
		}
		json << " ]";
		first = false;
		break;
	}
	if (!m_group.empty())
	{
		if (! first)
			json << ", ";
		json << "\"group\" : \"" << m_group << "\"";
		first = false;
	}
	switch (m_sort.size())
	{
	case 0:
		break;
	case 1:
		if (! first)
			json << ", ";
		json << "\"sort\" : " << m_sort.front()->toJSON();
		first = false;
		break;
	default:
		if (! first)
			json << ", ";
		json << "\"sort\" : [ ";
		for (auto it = m_sort.cbegin(); it != m_sort.cend(); ++it)
		{
			if (it != m_sort.cbegin())
				json << ", ";
			json << (*it)->toJSON();
		}
		json << " ], ";
		first = false;
		break;
	}
	if (m_timebucket)
	{
		if (! first)
			json << ", ";
		json << "\"timebucket\" : " << m_timebucket->toJSON();
		first = false;
	}
	if (m_limit)
	{
		if (! first)
			json << ", ";
		json << "\"limit\" : " << m_limit;
		first = false;
	}
	if (m_returns.size())
	{
		if (! first)
			json << ", ";
		json << "\"return\" : [ ";
		for (auto it = m_returns.cbegin(); it != m_returns.cend(); ++it)
		{
			if (it != m_returns.cbegin())
				json << ", ";
			json << (*it)->toJSON();
		}
		json << " ]";
		first = false;
	}
	if (m_distinct)
	{
		if (! first)
			json << ", ";
		json << "\"modifier\" : \"distinct\"";
		first = false;
	}
	json << " }";
	return json.str();
}

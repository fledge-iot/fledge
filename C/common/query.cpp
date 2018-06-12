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

Query::Query(Where *where) : m_where(where), m_limit(0), m_timebucket(0), m_distinct(false)
{
}

Query::Query(Aggregate *aggregate, Where *where) : m_where(where),
						   m_limit(0),
						   m_timebucket(0),
						   m_distinct(false)
{
	m_aggregates.push_back(aggregate);
}

Query::Query(Timebucket *timebucket, Where *where) : m_where(where),
						     m_limit(0),
						     m_timebucket(timebucket),
						     m_distinct(false)
{
}

Query::Query(Timebucket *timebucket, Where *where, unsigned int limit) : m_where(where),
									 m_limit(limit),
									 m_timebucket(timebucket),
									 m_distinct(false)
{
}

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

Query::Query(Returns *returns) : m_where(0),
				 m_limit(0),
				 m_timebucket(0),
				 m_distinct(false)
{
		m_returns.push_back(returns);
}

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

void Query::aggregate(Aggregate *aggregate)
{
	m_aggregates.push_back(aggregate);
}

void Query::sort(Sort *sort)
{
	m_sort.push_back(sort);
}

void Query::group(const string& column)
{
	m_group = column;
}

void Query::limit(unsigned int limit)
{
	m_limit = limit;
}

void Query::timebucket(Timebucket *timebucket)
{
	m_timebucket = timebucket;
}

void Query::returns(Returns *returns)
{
	m_returns.push_back(returns);
}

void Query::returns(vector<Returns *> returns)
{
	for (auto it = returns.cbegin(); it != returns.cend(); ++it)
	{
		m_returns.push_back(*it);
	}
}

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
		json << "\"returns\" : [ ";
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

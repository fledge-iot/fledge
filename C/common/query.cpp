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

Query::Query(Where *where) : m_where(where), m_limit(0), m_timebucket(0)
{
}

Query::Query(Aggregate *aggregate, Where *where) : m_where(where),
						   m_limit(0),
						   m_timebucket(0)
{
	m_aggregates.push_back(aggregate);
}

Query::Query(Timebucket *timebucket, Where *where) : m_where(where),
						     m_limit(0),
						     m_timebucket(timebucket)
{
}

Query::Query(Timebucket *timebucket, Where *where, unsigned int limit) : m_where(where),
									 m_limit(limit),
									 m_timebucket(timebucket)
{
}

Query::Query(vector<Returns *> returns, Where *where) : m_where(where),
							m_limit(0),
							m_timebucket(0)
{
	for (auto it = returns.cbegin(); it != returns.cend(); ++it)
	{
		m_returns.push_back(*it);
	}
}

Query::Query(vector<Returns *> returns, Where *where, unsigned int limit) : m_where(where),
									    m_limit(limit),
									    m_timebucket(0)
{
	for (auto it = returns.cbegin(); it != returns.cend(); ++it)
	{
		m_returns.push_back(*it);
	}
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

/**
 * Return the JSON payload for a where clause
 */
const string Query::toJSON() const
{
ostringstream json;

	json << "{ \"where\" : " << m_where->toJSON();
	switch (m_aggregates.size())
	{
	case 0:
		break;
	case 1:
		json << ", \"aggregate\" : " << m_aggregates.front()->toJSON();
		break;
	default:
		json << ", \"aggregate\" : [ ";
		for (auto it = m_aggregates.cbegin(); it != m_aggregates.cend(); ++it)
		{
			if (it != m_aggregates.cbegin())
				json << ", ";
			json << (*it)->toJSON();
		}
		json << " ]";
		break;
	}
	if (!m_group.empty())
	{
		json << ", \"group\" : \"" << m_group << "\"";
	}
	switch (m_sort.size())
	{
	case 0:
		break;
	case 1:
		json << ", \"sort\" : " << m_sort.front()->toJSON();
		break;
	default:
		json << ", \"sort\" : [ ";
		for (auto it = m_sort.cbegin(); it != m_sort.cend(); ++it)
		{
			if (it != m_sort.cbegin())
				json << ", ";
			json << (*it)->toJSON();
		}
		json << " ]";
		break;
	}
	if (m_timebucket)
	{
		json << ", \"timebucket\" : " << m_timebucket->toJSON();
	}
	if (m_limit)
	{
		json << ", \"limit\" : " << m_limit;
	}
	if (m_returns.size())
	{
		json << ", \"returns\" : [ ";
		for (auto it = m_returns.cbegin(); it != m_returns.cend(); ++it)
		{
			if (it != m_returns.cbegin())
				json << ", ";
			json << (*it)->toJSON();
		}
		json << " ]";
	}
	json << " }";
	return json.str();
}

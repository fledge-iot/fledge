#ifndef _QUERY_H
#define _QUERY_H
/*
 * FogLAMP storage client.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <where.h>
#include <aggregate.h>
#include <sort.h>
#include <timebucket.h>
#include <returns.h>
#include <string>
#include <vector>


/**
 * Storage layer query container
 */
class Query {
	public:
		Query(Where *where);
		Query(Aggregate *aggreate, Where *where);
		Query(Timebucket *timebucket, Where *where);
		Query(Timebucket *timebucket, Where *where, unsigned int limit);
		Query(Returns *returns);
		Query(std::vector<Returns *> returns);
		Query(std::vector<Returns *> returns, Where *where);
		Query(std::vector<Returns *> returns, Where *where, unsigned int limit);
		~Query();
		void				aggregate(Aggregate *aggegate);
		void				group(const std::string& column);
		void				sort(Sort *sort);
		void				limit(unsigned int limit);
		void				timebucket(Timebucket*);
		void				returns(Returns *);
		void				returns(std::vector<Returns *>);
		void				distinct();
		const std::string		toJSON() const;
	private:
		Query(const Query&);		// Disable copy of query
		Query& 				operator=(Query const&);
		Where				*m_where;
		std::vector<Aggregate *>	m_aggregates;
		std::string			m_group;
		std::vector<Sort *>		m_sort;
		unsigned int			m_limit;
		Timebucket*			m_timebucket;
		std::vector<Returns *>		m_returns;
		bool				m_distinct;
};
#endif


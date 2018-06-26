#ifndef _AGGREGRATE_H
#define _AGGREGRATE_H
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


/**
 * Aggregate clause in a selection of records
 */
class Aggregate {
	public:
		Aggregate(const std::string& operation, const std::string& column) :
				m_column(column), m_operation(operation) {};
		~Aggregate() {};
		std::string	toJSON();
	private:
		const std::string	m_column;
		const std::string	m_operation;
};
#endif


/*
 * Fledge storage service client
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <join.h>
#include <query.h>
#include <sstream>
#include <iostream>

using namespace std;

/**
 * Destructor fo rthe join clause
 */
Join::~Join()
{
	delete m_query;
}

/**
 * Convert a join clause to its JSON representation
 *
 * @return string	The JSON form of the join
 */
const string Join::toJSON() const
{
ostringstream   json;
bool 		first = true;

	json << " \"join\" : {";
	json << "\"table\" : { \"name\" : \"" << m_table << "\", ";
	json << "\"column\" : \"" << m_column << "\" }, ";
	json << "\"on\" : \"" << m_on << "\", ";
	json << "\"query\" : " << m_query->toJSON();
	json << " }";
	return json.str();
}

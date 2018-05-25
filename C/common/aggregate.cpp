/*
 * FogLAMP storage service client
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <aggregate.h>
#include <string>
#include <sstream>
#include <iostream>

using namespace std;


/**
 * Return the JSON payload for a where clause
 */
string Aggregate::toJSON()
{
ostringstream json;

	json << "{ \"column\" : \"" << m_column << "\",";
	json << " \"operation\" : \"" << m_operation << "\" }";
	return json.str();
}

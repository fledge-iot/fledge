/*
 * FogLAMP storage service client
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <where.h>
#include <string>
#include <sstream>
#include <iostream>

using namespace std;

/**
 * Where clause destructor
 */
Where::~Where()
{
	if (m_or)
	{
		delete m_or;
	}
	if (m_and)
	{
		delete m_and;
	}
}

/**
 * Return the JSON payload for a where clause
 */
const string Where::toJSON() const
{
ostringstream json;

	json << "{ \"column\" : \"" << m_column << "\", ";
	json << "\"condition\" : \"";
	switch (m_condition)
	{
	case Equals:
		json << "=";
		break;
	case NotEquals:
		json << "!=";
		break;
	case LessThan:
		json << "<";
		break;
	case GreaterThan:
		json << ">";
		break;
	}
	json << "\", ";
	json << "\"value\" : \"" << m_value << "\"";
	if (m_and || m_or)
	{
		if (m_and)
		{
			json << ", \"and\" : " << m_and->toJSON();
		}
		if (m_or)
		{
			json << ", \"or\" : " << m_or->toJSON();
		}
	}
	json << " }";
	return json.str();
}

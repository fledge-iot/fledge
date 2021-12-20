/*
 * Fledge storage service client
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
	case Older:
		json << "older";
		break;
	case Newer:
		json << "newer";
		break;
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
	case In:
		json << "in";
		break;
	}
	json << "\", ";

	if ( (m_condition == Older) || (m_condition == Newer) )
	{
		json << "\"value\" : " << m_value << "";

	}
	else if (m_condition != In)
	{
		json << "\"value\" : \"" << m_value << "\"";
	}
	else
	{
		json << "\"value\" : [";
		for (auto v = m_in.begin();
		     v != m_in.end();
		     ++v)
		{
			json << "\"" << *v << "\"";
			if (next(v, 1) != m_in.end())
			{
				json << ", ";
			}
		}
		json << "]";
	}

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

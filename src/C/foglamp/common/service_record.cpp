/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <service_record.h>
#include <string>
#include <sstream>

using namespace std;

/**
 * Constructor for the service record
 */
ServiceRecord::ServiceRecord(const string& name,
			     const string& type,
			     const string& protocol,
			     const string& address,
			     const short port) : m_name(name),
						 m_type(type),
						 m_protocol(protocol),
						 m_address(address),
						 m_port(port)
{
}

/**
 * Serialise the service record to json
 */
void ServiceRecord::asJSON(string& json) const
{
ostringstream convert;

	convert << "{ ";
	convert << "\"name\" : \"" << m_name << "\",";
	convert << "\"type\" : \"" << m_type << "\",";
	convert << "\"protocol\" : \"" << m_protocol << "\",";
	convert << "\"address\" : \"" << m_address << "\",";
	convert << "\"port\" : " << m_port;
	convert << "}";

	json = convert.str();
}

#ifndef _SERVICE_RECORD_H
#define _SERVICE_RECORD_H
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <json_provider.h>
#include <string>

class ServiceRecord : public JSONProvider {
	public:
		ServiceRecord(const std::string& name,
			      const std::string& type,
			      const std::string& protocol,
			      const std::string& address,
			      const unsigned short port,
			      const unsigned short managementPort);
		void asJSON(std::string &) const;
	private:
		std::string		m_name;
		std::string		m_type;
		std::string		m_protocol;
		std::string		m_address;
		unsigned short		m_port;
		unsigned short		m_managementPort;
};

#endif

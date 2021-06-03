#ifndef _SERVICE_RECORD_H
#define _SERVICE_RECORD_H
/*
 * Fledge storage service.
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
		ServiceRecord(const std::string& name);
		ServiceRecord(const std::string& name,
			      const std::string& type);
		ServiceRecord(const std::string& name,
			      const std::string& type,
			      const std::string& protocol,
			      const std::string& address,
			      const unsigned short port,
			      const unsigned short managementPort,
			      const std::string& token = "");
		void			asJSON(std::string &) const;
		const std::string&	getName() const
					{
						return m_name;
					}
		const std::string&	getType() const
					{
						return m_type;
					}
		void			setAddress(const std::string& address)
					{
						m_address = address;
					}
		void			setPort(const unsigned short port)
					{
						m_port = port;
					}
		void			setProtocol(const std::string& protocol)
					{
						m_protocol = protocol;
					}
		void			setManagementPort(const unsigned short managementPort)
					{
						m_managementPort = managementPort;
					}
		const std::string&	getAddress()
					{
						return m_address;
					}
		unsigned short		getPort()
					{
						return m_port;
					}
		bool			operator==(const ServiceRecord& b) const
					{
						return m_name.compare(b.m_name) == 0
							&& m_type.compare(b.m_type) == 0
							&& m_protocol.compare(b.m_protocol) == 0
							&& m_address.compare(b.m_address) == 0
							&& m_port == b.m_port
							&& m_managementPort == b.m_managementPort;
					}
	private:
		std::string		m_name;
		std::string		m_type;
		std::string		m_protocol;
		std::string		m_address;
		unsigned short		m_port;
		unsigned short		m_managementPort;
		std::string		m_token; // token set by core server at service start
};

#endif

#ifndef _MDNS_DISCOVERY_H
#define _MDNS_DISCPVERY_H

/*
 * MDNS Discovery class that will look for connected devices
 * and create the default configuration that supports
 * selection of discovered cameras from a list.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <zeroconf.hpp>
#include <config_category.h>
#include <logger.h>
#include <string>
#include <vector>
#include <map>


/**
 * A class that uses MDNS to find devices that offer a service
 * and add them to a configuration item in the default configuration
 * of a plugin.
 */
class MDNSDiscovery {
	public:
					MDNSDiscovery(const std::string& service);
					~MDNSDiscovery();
		char			*discover(const char *config, const char *item);
	private:
		std::string	m_service;
		void		*get_in_addr(sockaddr_storage* sa);
		Logger		*m_logger;
};
#endif

#ifndef _THINGSPEAK_H
#define _THINGSPEAK_H
/*
 * FogLAMP ThingSpeak north plugin.
 *
 * Copyright (c) 2018 Dianomic Systems
 *      
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>
#include <vector>
#include <reading.h>
#include <simple_https.h>

class ThingSpeak
{
	public:
		ThingSpeak(const std::string& url, const int channel, const std::string& apiKey);
		~ThingSpeak();
		void		connect();
		uint32_t	send(const std::vector<Reading *> readings);
	private:
		SimpleHttps	*m_https;
		std::string	m_url;
		std::string	m_apiKey;
		int		m_channel;
		std::vector<std::pair<std::string, std::string>>
				m_headers;
};
#endif

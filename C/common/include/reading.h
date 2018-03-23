#ifndef _READING_H
#define _READING_H
/*
 * FogLAMP storage client.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <datapoint.h>
#include <string>
#include <ctime>
#include <vector>

#define DEFAULT_DATE_TIME_FORMAT "%Y-%m-%d %H:%M:%S"
#define DATE_TIME_BUFFER_LEN     52

/**
 * An asset reading represented as a class.
 *
 * Each asset reading may have multiple datapoints to represent the
 * multiple values that maybe held within a complex asset.
 */
class Reading {
	public:
		Reading(const std::string& asset, Datapoint *value);
		Reading(const Reading& orig);
		~Reading();
		void		addDatapoint(Datapoint *value);
		std::string	toJSON();
	private:
		const std::string		m_asset;
		struct timeval			m_timestamp;
		std::vector<Datapoint *>	m_values;
		std::string			m_uuid;
};
#endif


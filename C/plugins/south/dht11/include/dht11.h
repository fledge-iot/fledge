#ifndef _DHT11_H
#define _DHT11_H
/*
 * FogLAMP south service plugin
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */
#include <reading.h>

#define MAX_TIMINGS      85

class DHT11 {
	public:
		DHT11(unsigned int pin);
		~DHT11();
		void            setAssetName(const std::string& assetName) { m_assetName = assetName; };
		std::string 	getAssetName() { return m_assetName; };
		Reading		takeReading(bool firstReading=false);
	private:
		unsigned int	m_pin;
		std::string     m_assetName;
		bool		readSensorData(uint8_t sensorData[]);
};
#endif

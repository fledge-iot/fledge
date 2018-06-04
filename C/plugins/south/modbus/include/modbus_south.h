#ifndef _MODBUS_H
#define _MODBUS_H
/*
 * FogLAMP south service plugin
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <reading.h>
#include <modbus/modbus.h>
#include <string>

class Modbus {
	public:
		Modbus(const std::string& ip, const unsigned short port);
		Modbus(const std::string& device, int baud, char parity, int bits, int stopBits);
		~Modbus();
		Reading		takeReading();
	private:
		modbus_t	*m_modbus;
};
#endif

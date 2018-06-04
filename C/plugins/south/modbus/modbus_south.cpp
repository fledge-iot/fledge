/*
 * FogLAMP south service plugin
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <modbus_south.h>
#include <reading.h>

using namespace std;

/**
 * Constructor for the modbus interface for a TCP connection
 */
Modbus::Modbus(const string& ip, const unsigned short port)
{
	m_modbus = modbus_new_tcp(ip.c_str(), port);
}

/**
 * Constructor for the modbus interface for a serial connection
 */
Modbus::Modbus(const string& device, int baud, char parity, int bits, int stopBits)
{
	m_modbus = modbus_new_rtu(device.c_str(), baud, parity, bits, stopBits);
}
/**
 * Destructor for the modbus interface
 */
Modbus::~Modbus()
{
}

/**
 * Take a reading from the random "sensor"
 */
Reading	Modbus::takeReading()
{
	DatapointValue value(1);
	return Reading("dummy", new Datapoint("random", value));
}

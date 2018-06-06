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
	for (vector<RegisterMap *>::const_iterator it = m_registers.cbegin();
			it != m_registers.cend(); ++it)
	{
		delete *it;
	}
	for (vector<RegisterMap *>::const_iterator it = m_coils.cbegin();
			it != m_coils.cend(); ++it)
	{
		delete *it;
	}
}

/**
 * Take a reading from the random "sensor"
 */
Reading	Modbus::takeReading()
{
vector<Datapoint *>	points;

	for (int i = 0; i < m_registers.size(); i++)
	{
		uint16_t	regValue;
		modbus_read_registers(m_modbus, m_registers[i]->m_registerNo, 1, &regValue);
		DatapointValue value(regValue);
		points.push_back(new Datapoint(m_registers[i]->m_name, value));
	}
	for (int i = 0; i < m_coils.size(); i++)
	{
		uint8_t	coilValue;
		modbus_read_bits(m_modbus, m_coils[i]->m_registerNo, 1, &coilValue);
		DatapointValue value(coilValue);
		points.push_back(new Datapoint(m_coils[i]->m_name, value));
	}
	return Reading(m_assetName, points);
}

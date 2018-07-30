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
Modbus::Modbus(const string& ip, const unsigned short port) :
	m_address(ip), m_port(port), m_device(""), m_tcp(true)
{
	m_modbus = modbus_new_tcp(ip.c_str(), port);
#if DEBUG
	modbus_set_debug(m_modbus, true);
#endif
	if (modbus_connect(m_modbus) == -1)
	{
		m_connected = false;
	}
	
}

/**
 * Constructor for the modbus interface for a serial connection
 */
Modbus::Modbus(const string& device, int baud, char parity, int bits, int stopBits) :
	m_device(device), m_address(""), m_port(0), m_tcp(false)
{
	m_modbus = modbus_new_rtu(device.c_str(), baud, parity, bits, stopBits);
	m_connected = true;
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
	modbus_free(m_modbus);
}

/**
 * Set the slave ID of the modbus node we are interacting with
 *
 * @param slave		The modbus slave ID
 */
void Modbus::setSlave(int slave)
{
	modbus_set_slave(m_modbus, slave);
}

/**
 * Take a reading from the modbus
 */
Reading	Modbus::takeReading()
{
vector<Datapoint *>	points;

	if ((!m_connected) && modbus_connect(m_modbus) != -1)
	{
		m_connected = true;
	}
	if (!m_connected)
	{
		return Reading(m_assetName, points);
	}
	for (int i = 0; i < m_coils.size(); i++)
	{
		uint8_t	coilValue;
		if (modbus_read_bits(m_modbus, m_coils[i]->m_registerNo, 1, &coilValue) == 1)
		{
			DatapointValue value(coilValue);
			points.push_back(new Datapoint(m_coils[i]->m_name, value));
		}
		else if (errno = EPIPE)
		{
			m_connected = false;
		}
	}
	for (int i = 0; i < m_inputs.size(); i++)
	{
		uint8_t	inputValue;
		if (modbus_read_input_bits(m_modbus, m_inputs[i]->m_registerNo, 1, &inputValue) == 1)
		{
			DatapointValue value(inputValue);
			points.push_back(new Datapoint(m_inputs[i]->m_name, value));
		}
		else if (errno = EPIPE)
		{
			m_connected = false;
		}
	}
	for (int i = 0; i < m_registers.size(); i++)
	{
		uint16_t	regValue;
		if (modbus_read_registers(m_modbus, m_registers[i]->m_registerNo, 1, &regValue) == 1)
		{
			DatapointValue value(regValue);
			points.push_back(new Datapoint(m_registers[i]->m_name, value));
		}
		else if (errno = EPIPE)
		{
			m_connected = false;
		}
	}
	for (int i = 0; i < m_inputRegisters.size(); i++)
	{
		uint16_t	regValue;
		if (modbus_read_input_registers(m_modbus, m_inputRegisters[i]->m_registerNo, 1, &regValue) == 1)
		{
			DatapointValue value(regValue);
			points.push_back(new Datapoint(m_inputRegisters[i]->m_name, value));
		}
		else if (errno = EPIPE)
		{
			m_connected = false;
		}
	}
	return Reading(m_assetName, points);
}

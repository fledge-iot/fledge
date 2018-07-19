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
		void		setSlave(int slave);
		void		setAssetName(const std::string& assetName) { m_assetName = assetName; };
		void		addRegister(const std::string& value, const unsigned int registerNo)
				{
					m_registers.push_back(new Modbus::RegisterMap(value, registerNo));
				};
		void		addCoil(const std::string& value, const unsigned int registerNo)
				{
					m_coils.push_back(new Modbus::RegisterMap(value, registerNo));
				};
		void		addInput(const std::string& value, const unsigned int registerNo)
				{
					m_inputs.push_back(new Modbus::RegisterMap(value, registerNo));
				};
		void		addInputRegister(const std::string& value, const unsigned int registerNo)
				{
					m_inputRegisters.push_back(new Modbus::RegisterMap(value, registerNo));
				};
		Reading		takeReading();
	private:
		Modbus(const Modbus&);
		Modbus & 		operator=(const Modbus&);
		class RegisterMap {
			public:
				RegisterMap(const std::string& value, const unsigned int registerNo) :
					m_name(value), m_registerNo(registerNo) {};
				const std::string		m_name;
				const unsigned int		m_registerNo;
		};
		modbus_t			*m_modbus;
		std::string			m_assetName;
		std::vector<RegisterMap *>	m_coils;
		std::vector<RegisterMap *>	m_inputs;
		std::vector<RegisterMap *>	m_registers;
		std::vector<RegisterMap *>	m_inputRegisters;
		const std::string		m_address;
		const unsigned short		m_port;
		const std::string		m_device;
		const bool			m_tcp;
		bool				m_connected;
};
#endif

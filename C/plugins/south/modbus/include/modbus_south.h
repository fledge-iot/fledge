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
		void		setAssetName(const std::string& assetName) { m_assetName = assetName; };
		void		addRegisterMap(const std::string& value, const unsigned int registerNo)
				{
					m_registerMap.push_back(new Modbus::RegisterMap(value, registerNo));
				};
		Reading		takeReading();
	private:
		Modbus(const Modbus&);
		Modbus & 		operator=(const Modbus&);
		class RegisterMap {
			public:
				RegisterMap(const std::string& value, const unsigned int registerNo);
				const std::string		m_name;
				const unsigned int		m_registerNo;
		};
		modbus_t			*m_modbus;
		std::string			m_assetName;
		std::vector<RegisterMap *>	m_registerMap;
};
#endif

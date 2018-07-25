#ifndef _USB4704_H
#define _USB4704_H
/*
 * FogLAMP south service plugin
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <reading.h>
#include <string>
#include <vector>
#include <bdaqctrl.h>
#include <exception>

class USB4704
{
	public:
		USB4704();
		~USB4704();
		void			setAssetName(const std::string& asset);
		void			addAnalogueConnection(const std::string& name, const std::string& pin, double scale);
		Reading			takeReading();
	private:
		class Analogue {
			public:
				Analogue(const std::string& name, const std::string& pin, double scale);
				std::string 	getName() { return m_name; };
				double		getValue(Automation::BDaq::InstantAiCtrl *ctrl);
			private:
				std::string	m_name;
				double		m_scale;
				std::string	m_pinName;
				int32_t		m_channel;
				
		};
		std::string				m_asset;
		std::vector<Analogue *>			m_analogue;
		Automation::BDaq::InstantAiCtrl		*m_instantAiCtrl;
		int					m_analogueChannelMax;
};

class InvalidPin : public std::exception
{
	public:
		InvalidPin(const std::string& pin) : m_pin(pin) {};
		virtual const char *what() const throw()
		{
			std::string msg = "Invalid pin definition " + m_pin;
			return msg.c_str();
		}
	private:
		std::string	m_pin;
};

class USB4704InitialisationFailed : public std::exception
{
	public:
		virtual const char *what() const throw()
                {
			return "Failed to initialise USB4704";
		}
};
#endif

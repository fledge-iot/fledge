/*
 * FogLAMP south service plugin
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <usb4704.h>
#include <reading.h>
#include <bdaqctrl.h>
#include <logger.h>

#define      deviceDescription  L"USB-4704,BID#0"

using namespace std;
using namespace Automation::BDaq;

/**
 * Constructor fo rthe USB-4704 generic capture device plugin
 */
USB4704::USB4704() : m_asset("usb4704"), m_instantAiCtrl(0)
{
}

/**
 * Destructor fo rthe USB-4704 generic capture device plugin
 */
USB4704::~USB4704()
{
	for (vector<Analogue *>::const_iterator it = m_analogue.cbegin();
                        it != m_analogue.cend(); ++it)
        {
                delete *it;
        }
	for (vector<Digital *>::const_iterator it = m_digital.cbegin();
                        it != m_digital.cend(); ++it)
        {
                delete *it;
        }
}

/**
 * Add a new analogue pin to be monitored by the plugin
 *
 * @param name	The name of the datapoint that will be added for this analogue channel
 * @param pin	The string name of the pin to read
 * @param scale	A scaling multiplier to be applied to values read
 */
void USB4704::addAnalogueConnection(const string& name, const string& pin, double scale)
{
	// If it is the first analogue channel create the AiCtrl
	if (m_instantAiCtrl == 0)
	{
		m_instantAiCtrl = AdxInstantAiCtrlCreate();
		DeviceInformation devInfo(deviceDescription);
		ErrorCode ret = m_instantAiCtrl->setSelectedDevice(devInfo);
		if (BioFailed(ret))
		{
			Logger::getLogger()->error("Failed to initialise USB-4704, error code %x", ret);
			throw USB4704InitialisationFailed();
		}
		m_analogueChannelMax = m_instantAiCtrl->getFeatures()->getChannelCountMax();
	}

	m_analogue.push_back(new Analogue(name, pin, scale));
}

/**
 * Add a new set of digital pins to be monitored by the plugin
 *
 * @param name	The name of the datapoint that will be added for this analogue channel
 * @param pins	The string name of the pins to read
 */
void USB4704::addDigitalConnection(const string& name, const vector<string>& pins)
{
	// If it is the first analogue channel create the AiCtrl
	if (m_instantDiCtrl == 0)
	{
		m_instantDiCtrl = AdxInstantDiCtrlCreate();
		DeviceInformation devInfo(deviceDescription);
		ErrorCode ret = m_instantDiCtrl->setSelectedDevice(devInfo);
		if (BioFailed(ret))
		{
			Logger::getLogger()->error("Failed to initialise USB-4704, error code %x", ret);
			throw USB4704InitialisationFailed();
		}
	}

	m_digital.push_back(new Digital(name, pins));
}

/**
 * Take a reading of each of the analogue or digital pins we are monitoring
 */
Reading USB4704::takeReading()
{
vector<Datapoint *> points;

	for (int i = 0; i < m_analogue.size(); i++)
	{
		Analogue *pin = m_analogue[i];
		double value;

		// Read value from A/D
		DatapointValue val(pin->getValue(m_instantAiCtrl));
		points.push_back(new Datapoint(pin->getName(), val));
	}
	for (int i = 0; i < m_digital.size(); i++)
	{
		Digital *pin = m_digital[i];
		double value;

		// Read value from digital pins
		DatapointValue val((int)(pin->getValue(m_instantDiCtrl)));
		points.push_back(new Datapoint(pin->getName(), val));
	}
	return Reading(m_asset, points);
}

/**
 * Constructor for an analogue channel
 *
 * @param name	The name to return in readings for this channel
 * @param pin	The pin name of the channel, e.g. AI0
 * @param scale	A scale factor to multiple channel readings by
 * @throws exception If an invalid channel name is supplied
 */
USB4704::Analogue::Analogue(const string& name, const string& pin, double scale) :
				m_name(name), m_pinName(pin), m_scale(scale)
{
	if (pin.compare(0, 2, "AI") != 0)
	{
		Logger::getLogger()->error("USB-4704 invalid pin definition %s, only abnalogue pins can be specified", pin.c_str());
		throw InvalidPin(pin);
	}
	m_channel = atoi(&(pin.c_str())[2]);
	if (m_channel < 0 || m_channel > 7)
	{
		Logger::getLogger()->error("USB-4704 invalid pin definition %s, pin is out of range", pin.c_str());
		throw InvalidPin(pin);
	}

}

/**
 * Return a scaled value for the analogue channel
 *
 * @return double	The scaled value on the A/D channel
 */
double USB4704::Analogue::getValue(InstantAiCtrl *ctrl)
{
double value = 0.0;

	ctrl->Read(m_channel, 1, &value);
	value *= m_scale;
	return value;
}

/**
 * Constructor for a digital channel
 *
 * @param name	The name to return in readings for this channel
 * @param pins	The set of pins to include in the reading
 * @throws exception If an invalid channel name is supplied
 */
USB4704::Digital::Digital(const string& name, const vector<string>& pins) :
				m_name(name), m_pinMask(0)
{
	for (vector<string>::const_iterator it = pins.cbegin(); it != pins.cend(); it++)
	{
		if (it->compare(0, 2, "DI") != 0)
		{
			Logger::getLogger()->error("USB-4704 invalid pin definition %s, only digital input pins may be specified", it->c_str());
			throw InvalidPin(*it);
		}
		int channel = atoi(&(it->c_str())[2]);
		if (channel < 0 || channel > 7)
		{
			Logger::getLogger()->error("USB-4704 invalid pin definition, digital channel out of range");
			throw InvalidPin(*it);
		}
		m_pinMask |= 1 << channel;
	}

}

/**
 * Return a scaled value for the analogue channel
 *
 * @return uint8_t	The value of the selected digital channels
 */
uint8_t  USB4704::Digital::getValue(InstantDiCtrl *ctrl)
{
uint8_t value = 0, tmp;

	ctrl->Read(0, 8, &tmp);	// Read all channels and masl what we want later
	for (int i = 0; i < 8; i++)
	{
		if (tmp & (1 << i))
		{
			value <<= 1;
			value |= (tmp & (1 << i)) ? 1 : 0;
		}
	}
	return value;
}

/*
 * FogLAMP south service plugin
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <ina219.h>
#include <wiringPiI2C.h>
#include <reading.h>
#include <logger.h>

using namespace std;

/**
 * Constructor for the INA219 plugin
 */
INA219::INA219(int address) : m_address(address)
{
}

/**
 * Destructor for the ina219 interface
 */
INA219::~INA219()
{
}

/**
 * Set the asset name for the asset we write
 *
 * @param asset Set the name of the asset with insert into readings
 */
void
INA219::setAssetName(const std::string& asset)
{
	m_asset = asset;
}

/**
 * Configuration the range of the INA219 - this let's
 * us trade off accuracy verses range.
 *
 * @param conf		The required configuration
 */
void
INA219::configure(INA219_CONFIGURATION conf)
{
uint16_t config = 0;

	if ((m_fd = wiringPiI2CSetup(m_address)) == -1)
	{
		Logger::getLogger()->error("Unable to initialise I2C");
		return;
	}

	switch (conf)
	{
	case CONF_16V_400MA:
		m_calValue = 8192;
		m_powerMultiplier = 1;
		m_currentDivider = 20;
		config = INA219_CONFIG_BVOLTAGERANGE_16V |
                    INA219_CONFIG_GAIN_40MV |
                    INA219_CONFIG_BADCRES_12BIT |
                    INA219_CONFIG_SADCRES_12BIT_1S_532US |
                    INA219_CONFIG_MODE_SANDBVOLT_CONTINUOUS;
		break;
        case CONF_32V_1A:
		m_calValue = 10240;
		m_powerMultiplier = 1;
		m_currentDivider = 25;
		config = INA219_CONFIG_BVOLTAGERANGE_32V |
                    INA219_CONFIG_GAIN_320MV |
                    INA219_CONFIG_BADCRES_12BIT |
                    INA219_CONFIG_SADCRES_12BIT_1S_532US |
                    INA219_CONFIG_MODE_SANDBVOLT_CONTINUOUS;
		break;
        case CONF_32V_2A:
	default:
		m_calValue = 4096;
		m_powerMultiplier = 2;
		m_currentDivider = 10;
		config = INA219_CONFIG_BVOLTAGERANGE_32V |
                    INA219_CONFIG_GAIN_320MV |
                    INA219_CONFIG_BADCRES_12BIT |
                    INA219_CONFIG_SADCRES_12BIT_1S_532US |
                    INA219_CONFIG_MODE_SANDBVOLT_CONTINUOUS;
		break;
	}

	wiringPiI2CWriteReg16(m_fd, INA219_REG_CALIBRATION, m_calValue);
	wiringPiI2CWriteReg16(m_fd, INA219_REG_CONFIG, config);
}

/**
 * Take a reading from the INA219
 */
Reading	INA219::takeReading()
{
vector<Datapoint *>	points;

	double shuntVolts  = wiringPiI2CReadReg16(m_fd, INA219_REG_SHUNTVOLTAGE) * 0.01;
	double busVolts  = wiringPiI2CReadReg16(m_fd, INA219_REG_BUSVOLTAGE) * 0.001;
	double volts = busVolts + (shuntVolts / 1000);
	DatapointValue value2(volts);
	points.push_back(new Datapoint("voltage", value2));
	wiringPiI2CWriteReg16(m_fd, INA219_REG_CALIBRATION, m_calValue);
	double current  = wiringPiI2CReadReg16(m_fd, INA219_REG_CURRENT) / m_currentDivider;
	DatapointValue value3(current);
	points.push_back(new Datapoint("current", value3));
	double power  = wiringPiI2CReadReg16(m_fd, INA219_REG_POWER) * m_powerMultiplier;
	DatapointValue value4(power);
	points.push_back(new Datapoint("power", value4));
	return Reading(m_asset, points);
}

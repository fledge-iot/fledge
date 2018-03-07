/*
 * FogLAMP south service plugin
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <random.h>
#include <reading.h>

/**
 * Constructor for the random "sensor"
 */
Random::Random()
{
	srand(time(0));
	m_lastValue = rand() % 100;
}

/**
 * Destructor for the random "sensor"
 */
Random::~Random()
{
}

/**
 * Take a reading from the random "sensor"
 */
Reading	Random::takeReading()
{
	m_lastValue += ((rand() % 100) > 50 ? 1 : -1) *
		((rand() % 100) / 20);
	DatapointValue value(m_lastValue);
	return Reading("dummy", new Datapoint("random", value));
}

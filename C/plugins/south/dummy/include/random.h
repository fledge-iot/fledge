#ifndef _RANDOM_H
#define _RANDOM_H
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

class Random {
	public:
		Random();
		~Random();
		Reading		takeReading();
	private:
		int		m_lastValue;
};
#endif

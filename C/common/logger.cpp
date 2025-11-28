/*
 * Fledge Logger base class
 *
 * Copyright (c) 2017-2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include "logger.h"

/**
 * The singleton pointer
 */
Logger *Logger::instance = 0;

/**
 * Logger Class virtual destructor
 */
Logger::~Logger()
{
	// Stop the getLogger() call returning a deleted instance
	if (instance == this)
		instance = NULL;
	else if (!instance)
		return;	// Already destroyed
}

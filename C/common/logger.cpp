/*
 * Fledge Logger base class
 *
 * Copyright (c) 2017-2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <logger.h>
#include <stdio.h>
#include <unistd.h>
#include <syslog.h>
#include <stdarg.h>
#include <memory>
#include <string.h>
#include <sys/time.h>
#include <sys/socket.h>
#include <exception>
#include <arpa/inet.h>
#include <stdexcept>
#include <algorithm>

// /**
//  * The singleton pointer
//  */
Logger *Logger::instance = 0;

// /**
//  * Destructor for the logger class.
//  */
Logger::~Logger()
{
	// Stop the getLogger() call returning a deleted instance
	if (instance == this)
		instance = NULL;
	else if (!instance)
		return;	// Already destroyed
}

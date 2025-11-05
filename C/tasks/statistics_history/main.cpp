/*
 * Fledge statistics history task
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <stats_history.h>

using namespace std;

int main(int argc, char** argv)
{
	try
	{
		// Instantiate StatsHistory class
		StatsHistory statisticsHistory(argc, argv);

		statisticsHistory.run();

	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->fatal("Exception %s starting Stats History task", e.what());
		// Return failure for class instance/configuration etc
		exit(1);
	}
	// Catch all exceptions
	catch (...)
	{
		std::exception_ptr p = std::current_exception();
		string name = (p ? p.__cxa_exception_type()->name() : "null");
		Logger::getLogger()->fatal("Exception %s starting Stats History task", name);
		exit(1);
	}

	// Return success
	exit(0);
}

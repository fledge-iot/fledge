/*
 * Fledge statistics history task
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <purge_system.h>
#include <logger.h>

using namespace std;

int main(int argc, char** argv)
{
	try
	{
		// Instantiate StatsHistory class
		PurgeSystem PurgeSystem(argc, argv);

		PurgeSystem.run();

	}
	catch (const std::exception& e)
	{
		cerr << "Exception " << e.what() << endl;
		exit(1);
	}
	catch (...)
	{
		std::exception_ptr p = std::current_exception();
		string name = (p ? p.__cxa_exception_type()->name() : "null");
		cerr << "Generic Exception" << name << endl;
		exit(1);
	}

	// Return success
	exit(0);
}

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
	Logger *logger = new Logger(LOG_NAME);

	try
	{
		PurgeSystem PurgeSystem(argc, argv);

		PurgeSystem.run();
	}
	catch (const std::exception& e)
	{
		logger->error("An error occurred during the execution, :%s: ", e.what());
		exit(1);
	}
	catch (...)
	{
		std::exception_ptr p = std::current_exception();
		string name = (p ? p.__cxa_exception_type()->name() : "null");

		logger->error("An error occurred during the execution, :%s: ", name.c_str() );
		exit(1);
	}

	// Return success
	exit(0);
}

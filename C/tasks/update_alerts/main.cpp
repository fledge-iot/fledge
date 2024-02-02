/*
 * Fledge Update Alerts
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <update_alerts.h>
#include <logger.h>

using namespace std;

int main(int argc, char** argv)
{
	Logger *logger = new Logger(LOG_NAME);

	try
	{
		UpdateAlerts PurgeSystem(argc, argv);

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

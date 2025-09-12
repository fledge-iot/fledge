/*
 * Fledge Check Updates
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <check_updates.h>
#include <logger.h>

using namespace std;

int main(int argc, char** argv)
{
	try
	{
		CheckUpdates check(argc, argv);

		check.run();
	}
	catch (...)
	{
		try
                {
                        std::exception_ptr p = std::current_exception();
                        std::rethrow_exception(p);
                }
                catch(const std::exception& e)
                {
			Logger::getLogger()->error("An error occurred during the execution : %s", e.what());
                }

		exit(1);
	}

	// Return success
	exit(0);
}

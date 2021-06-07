#ifndef _PURGE_SYSTEM_H
#define _PURGE_SYSTEM_H

/*
 * Fledge Statistics History
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <process.h>

class PurgeSystem : public FledgeProcess
{
	public:
		PurgeSystem(int argc, char** argv);
		~PurgeSystem();

		void     run() const;

	private:
		void     processEnd() const;
};

#endif

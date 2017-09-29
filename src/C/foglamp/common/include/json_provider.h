#ifndef _JSONPROVIDER_H
#define _JSONPROVIDER_H
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>

class JSONProvider
{
	public:
		virtual void	asJSON(std::string &) const = 0;
};
#endif

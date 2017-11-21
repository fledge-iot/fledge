#ifndef _SERVICE_HANDLER_H
#define _SERVICE_HANDLER_H
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

/**
 * SewrviceHandler abstract class - the interface that services using the
 * management API must provide.
 */
class ServiceHandler
{
	public:
		virtual void	shutdown() = 0;
		virtual void	configChange(const std::string& category, const std::string& payload) = 0;
};
#endif

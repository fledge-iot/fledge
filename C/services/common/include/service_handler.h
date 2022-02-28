#ifndef _SERVICE_HANDLER_H
#define _SERVICE_HANDLER_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <config_category.h>
#include <string>

/**
 * ServiceHandler abstract class - the interface that services using the
 * management API must provide.
 */
class ServiceHandler
{
	public:
		virtual void	shutdown() = 0;
		virtual void	configChange(const std::string& category, const std::string& config) = 0;
		virtual void	configChildCreate(const std::string& parent_category, const std::string& category, const std::string& config) = 0;
		virtual void	configChildDelete(const std::string& parent_category, const std::string& category) = 0;
		virtual bool	isRunning() = 0;
};
#endif

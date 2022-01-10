#ifndef _CONFIG_HANDLER_H
#define _CONFIG_HANDLER_H
/*
 * Fledge 
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <service_handler.h>
#include <management_client.h>
#include <config_category.h>
#include <logger.h>
#include <string>
#include <map>
#include <mutex>

typedef std::multimap<std::string, ServiceHandler *> CONFIG_MAP;

/**
 * Handler class within a service to manage configuration changes
 */
class ConfigHandler {
	public:
		static ConfigHandler	*getInstance(ManagementClient *);
		void			configChange(const std::string& category, const std::string& config);
		void            configChildCreate(const std::string& parent_category, const std::string& child_category, const std::string& config);
		void            configChildDelete(const std::string& parent_category, const std::string& child_category);
		void			registerCategory(ServiceHandler *handler,
							 const std::string& category);
		void 			registerCategoryChild(ServiceHandler *handler, const std::string& category);

		void			unregisterCategory(ServiceHandler *handler, const std::string& category);
		static ConfigHandler	*instance;
	private:
		ConfigHandler(ManagementClient *);
		~ConfigHandler();
		ManagementClient	*m_mgtClient;
		CONFIG_MAP		m_registrations;
		CONFIG_MAP		m_registrationsChild;
		Logger			*m_logger;
		std::mutex		m_mutex;
		bool			m_change;
};
#endif

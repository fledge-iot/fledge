#ifndef _PROCESS_H
#define _PROCESS_H
/*
 * FogLAMP process base class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <storage_client.h>
#include <management_client.h>
#include <string.h>

/**
 * FogLAMP process base class
 */
class FogLampProcess
{
	public:
		FogLampProcess(int argc, char** argv);
		virtual ~FogLampProcess();
		StorageClient*          getStorageClient() const;
		ManagementClient*	getManagementClient() const;
		Logger			*getLogger() const;
    		std::string	    	getName() const { return m_name; };

	    	time_t			getStartTime() const { return m_stime; };

	protected:
		std::string getArgValue(const std::string& name) const;

	private:
		const time_t		m_stime;    // Start time
		const int		m_argc;
		const char**		m_arg_vals;
		// FogLAMP core management service details
		std::string		m_name;
		int			m_core_mngt_port;
		std::string		m_core_mngt_host;
		ManagementClient* 	m_client;
		StorageClient*		m_storage;
		Logger*			m_logger;
};

#endif

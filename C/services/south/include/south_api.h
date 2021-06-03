#ifndef _SOUTH_API_H
#define _SOUTH_API_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2021  Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <logger.h>
#include <server_http.hpp>

#define SETPOINT	"^/fledge/south/setpoint$"
#define OPERATION	"^/fledge/south/operation$"

class SouthService;

class SouthApi {
	public:
		SouthApi(SouthService *);
		~SouthApi();
		unsigned short		getListenerPort();
		void			setPoint(std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Response> response,
							std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Request> request);
		void			operation(std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Response> response,
							std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Request> request);
		void			startServer();

	private:
		SimpleWeb::Server<SimpleWeb::HTTP>
					*m_server;
		SouthService		*m_service;
		std::thread		*m_thread;
		Logger			*m_logger;
};

#endif

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

// Debugger URLs
#define DEBUG_ATTACH		"^/fledge/south/debug/attach$"
#define DEBUG_DETACH		"^/fledge/south/debug/detach$"
#define DEBUG_BUFFER		"^/fledge/south/debug/buffer$"
#define DEBUG_ISOLATE		"^/fledge/south/debug/isolate$"
#define DEBUG_SUSPEND		"^/fledge/south/debug/suspend$"
#define DEBUG_STEP		"^/fledge/south/debug/step$"
#define DEBUG_REPLAY		"^/fledge/south/debug/replay$"
#define DEBUG_STATE		"^/fledge/south/debug/state$"

class SouthService;

typedef std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Response> Response;
typedef std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Request> Request;

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

		// Debugger entry points
		void			attachDebugger(Response response, Request request);
		void			detachDebugger(Response response, Request request);
		void			setDebuggerBuffer(Response response, Request request);
		void			getDebuggerBuffer(Response response, Request request);
		void			isolateDebugger(Response response, Request request);
		void			suspendDebugger(Response response, Request request);
		void			stepDebugger(Response response, Request request);
		void			replayDebugger(Response response, Request request);
		void			stateDebugger(Response response, Request request);

	private:
		SimpleWeb::Server<SimpleWeb::HTTP>
					*m_server;
		SouthService		*m_service;
		std::thread		*m_thread;
		Logger			*m_logger;
};

#endif

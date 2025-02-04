#ifndef _NORTH_API_H
#define _NORTH_API_H
/*
 * Fledge north service API.
 *
 * Copyright (c) 2025  Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <logger.h>
#include <server_http.hpp>

// Debugger URLs
#define DEBUG_ATTACH		"^/fledge/south/debug/attach$"
#define DEBUG_DETACH		"^/fledge/south/debug/detach$"
#define DEBUG_BUFFER		"^/fledge/south/debug/buffer$"
#define DEBUG_ISOLATE		"^/fledge/south/debug/isolate$"
#define DEBUG_SUSPEND		"^/fledge/south/debug/suspend$"
#define DEBUG_STEP		"^/fledge/south/debug/step$"
#define DEBUG_REPLAY		"^/fledge/south/debug/replay$"
#define DEBUG_STATE		"^/fledge/south/debug/state$"

class NorthService;

typedef std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Response> Response;
typedef std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Request> Request;

class NorthApi {
	public:
		NorthApi(NorthService *);
		~NorthApi();
		unsigned short		getListenerPort();
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
		NorthService		*m_service;
		std::thread		*m_thread;
		Logger			*m_logger;
};

#endif

/**
 * Fledge north service API
 *
 * Copyright (c) 2025 Dianomic Systems
 *
 * Author: Mark Riddoch
 */

#include <north_api.h>
#include <north_service.h>
#include <rapidjson/document.h>

using namespace std;
using namespace rapidjson;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

static NorthApi *api = NULL;

/**
 * Wrapper for the PUT attach debugger API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void attachDebuggerWrapper(Response response, Request request)
{
	if (api)
		api->attachDebugger(response, request);
}

/**
 * Wrapper for the PUT detach debugger API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void detachDebuggerWrapper(Response response, Request request)
{
	if (api)
		api->detachDebugger(response, request);
}

/**
 * Wrapper for the PUT set debugger buffer size API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void setDebuggerBufferWrapper(Response response, Request request)
{
	if (api)
		api->setDebuggerBuffer(response, request);
}

/**
 * Wrapper for the GET debugger buffer API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void getDebuggerBufferWrapper(Response response, Request request)
{
	if (api)
		api->getDebuggerBuffer(response, request);
}

/**
 * Wrapper for the PUT debugger isolate API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void isolateDebuggerWrapper(Response response, Request request)
{
	if (api)
		api->isolateDebugger(response, request);
}

/**
 * Wrapper for the PUT debugger suspend API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void suspendDebuggerWrapper(Response response, Request request)
{
	if (api)
		api->suspendDebugger(response, request);
}

/**
 * Wrapper for the PUT step debugger API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void stepDebuggerWrapper(Response response, Request request)
{
	if (api)
		api->stepDebugger(response, request);
}

/**
 * Wrapper for the PUT replay debugger API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void replayDebuggerWrapper(Response response, Request request)
{
	if (api)
		api->replayDebugger(response, request);
}

/**
 * Wrapper for the GET state debugger API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void stateDebuggerWrapper(Response response, Request request)
{
	if (api)
		api->stateDebugger(response, request);
}

/**
 * Wrapper for thread creation that is used to start the API
 */
static void startService()
{
	api->startServer();
}

/**
 * North API class constructor
 *
 * @param service	The NorthService class this is the API for
 */
NorthApi::NorthApi(NorthService *service) : m_service(service), m_thread(NULL)
{
	m_logger = Logger::getLogger();
	m_server = new HttpServer();
	m_server->config.port = 0;
	m_server->config.thread_pool_size = 1;

	// Add the debugger entry points
	m_server->resource[DEBUG_ATTACH]["PUT"] = attachDebuggerWrapper;
	m_server->resource[DEBUG_DETACH]["PUT"] = detachDebuggerWrapper;
	m_server->resource[DEBUG_BUFFER]["POST"] = setDebuggerBufferWrapper;
	m_server->resource[DEBUG_BUFFER]["GET"] = getDebuggerBufferWrapper;
	m_server->resource[DEBUG_ISOLATE]["PUT"] = isolateDebuggerWrapper;
	m_server->resource[DEBUG_SUSPEND]["PUT"] = suspendDebuggerWrapper;
	m_server->resource[DEBUG_STEP]["PUT"] = stepDebuggerWrapper;
	m_server->resource[DEBUG_REPLAY]["PUT"] = replayDebuggerWrapper;
	m_server->resource[DEBUG_STATE]["GET"] = stateDebuggerWrapper;

	api = this;
	m_thread = new thread(startService);
}

/**
 * Destroy the API.
 *
 * Stop the service and wait for the thread to terminate.
 */
NorthApi::~NorthApi()
{
	if (m_thread)
	{
		m_server->stop();
		m_thread->join();
		delete m_thread;
	}
	if (m_server)
		delete m_server;
}

/**
 * Called on the API service thread. Start the listener for HTTP requests
 */
void NorthApi::startServer()
{
	m_server->start();
}

/**
 * Return the port the service is listening on
 */
unsigned short NorthApi::getListenerPort()
{
	int max_wait = 10;
	// Need to make sure the server thread has started
	while (m_server->getLocalPort() == 0 && max_wait-- > 0)
		usleep(100);
	return m_server->getLocalPort();
}

/**
 * Invoke debugger attach on the north plugin
 *
 * @param response	The HTTP response
 * @param request	The HTTP request - unused
 */
void NorthApi::attachDebugger(Response response, Request /*request*/)
{
	if (m_service->allowDebugger())
	{
		bool status = m_service->attachDebugger();

		if (status)
		{
			string responsePayload = QUOTE({ "status" : "ok" });
			m_service->respond(response, responsePayload);
		}
		else
		{
			string responsePayload = QUOTE({ "status" : "Failed to attach the debugger to the pipeline" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
		}
	}
	else
	{	string responsePayload = QUOTE({ "status" : "Pipeline debugger features have been disabled" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
	}
}

/**
 * Invoke debugger detach on the north plugin
 *
 * @param response	The HTTP response
 * @param request	The HTTP request - unused
 */
void NorthApi::detachDebugger(Response response, Request /*request*/)
{
	if (m_service->allowDebugger())
	{
		string responsePayload;
		if (m_service->debuggerAttached())
		{
			m_service->detachDebugger();
			responsePayload = QUOTE({ "status" : "ok" });
		}
		else
		{
			responsePayload = QUOTE({"status" : "Debugger is not attached to the service" });
		}
		m_service->respond(response, responsePayload);
	}
	else
	{	string responsePayload = QUOTE({ "status" : "Pipeline debugger features have been disabled" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
	}
}

/**
 * Invoke set debugger buffer size on the north plugin
 *
 * @param response	The HTTP response
 * @param request	The HTTP request
 */
void NorthApi::setDebuggerBuffer(Response response, Request request)
{
	if (m_service->allowDebugger())
	{
		if (m_service->debuggerAttached())
		{
			string payload = request->content.string();
			Document doc;
			ParseResult result = doc.Parse(payload.c_str());
			if (result)
			{
				if (doc.HasMember("size"))
				{
					if (doc["size"].IsUint())
					{
						unsigned int size = doc["size"].GetUint();
						m_service->setDebuggerBuffer(size);

						string responsePayload = QUOTE({ "status" : "ok" });
						m_service->respond(response, responsePayload);
					}
					else
					{
						string responsePayload = QUOTE({ "message" : "The value of 'size' should be an unsigned integer" });
						m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
					}
				}
				else
				{
					string responsePayload = QUOTE({ "message" : "Missing 'size' item in payload" });
					m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
				}
			}
			else
			{
				string responsePayload = QUOTE({ "message" : "Failed to parse request payload" });
				m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
			}
		}
		else
		{
			string responsePayload = QUOTE({"status" : "Debugger is not attached to the service" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
		}
	}
	else
	{	string responsePayload = QUOTE({ "status" : "Pipeline debugger features have been disabled" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
	}
}

/**
 * Invoke get debugger buffer size on the north plugin
 *
 * @param response	The HTTP response
 * @param request	The HTTP request - unused
 */
void NorthApi::getDebuggerBuffer(Response response, Request /*request*/)
{
	if (m_service->allowDebugger())
	{
		string result;
		if (m_service->debuggerAttached())
		{
			result = m_service->getDebuggerBuffer();
		}
		else
		{
			result = QUOTE({"status" : "Debugger is not attached to the service" });
		}
		m_service->respond(response, result);
	}
	else
	{	string responsePayload = QUOTE({ "status" : "Pipeline debugger features have been disabled" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
	}
}

/**
 * Invoke isolate debugger handler on the north plugin
 *
 * @param response	The HTTP response
 * @param request	The HTTP request
 */
void NorthApi::isolateDebugger(Response response, Request request)
{
	if (m_service->allowDebugger())
	{
		if (m_service->debuggerAttached())
		{
			string payload = request->content.string();
			Document doc;
			ParseResult result = doc.Parse(payload.c_str());
			if (result)
			{
				if (doc.HasMember("state"))
				{
					if (doc["state"].IsString())
					{
						string state = doc["state"].GetString();
						if (state.compare("discard") == 0)
							m_service->isolateDebugger(true);
						else if (state.compare("store") == 0)
							m_service->isolateDebugger(false);
						else
						{
							string responsePayload = QUOTE({ "message" : "The value of 'state' should be one of 'discard' or 'store'" });
							m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
							return;
						}

						string responsePayload = QUOTE({ "status" : "ok" });
						m_service->respond(response, responsePayload);
					}
					else
					{
						string responsePayload = QUOTE({ "message" : "The value of 'size' should be a string with either 'discard' or 'store'." });
						m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
					}
				}
				else
				{
					string responsePayload = QUOTE({ "message" : "Missing 'state' item in payload" });
					m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
				}
			}
			else
			{
				string responsePayload = QUOTE({ "message" : "Failed to parse request payload" });
				m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
			}
		}
		else
		{
			string responsePayload = QUOTE({"status" : "Debugger is not attached to the service" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
		}
	}
	else
	{	string responsePayload = QUOTE({ "status" : "Pipeline debugger features have been disabled" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
	}
}

/**
 * Invoke suspend debugger handler on the north plugin
 *
 * @param response	The HTTP response
 * @param request	The HTTP request
 */
void NorthApi::suspendDebugger(Response response, Request request)
{
	if (m_service->allowDebugger())
	{
		if (m_service->debuggerAttached())
		{
			string payload = request->content.string();
			Document doc;
			ParseResult result = doc.Parse(payload.c_str());
			if (result)
			{
				if (doc.HasMember("state"))
				{
					if (doc["state"].IsString())
					{
						string state = doc["state"].GetString();
						if (state.compare("suspend") == 0)
							m_service->suspendDebugger(true);
						else if (state.compare("resume") == 0)
							m_service->suspendDebugger(false);
						else
						{
							string responsePayload = QUOTE({ "message" : "The value of 'state' should be one of 'suspend' or 'resume'" });
							m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
							return;
						}

						string responsePayload = QUOTE({ "status" : "ok" });
						m_service->respond(response, responsePayload);
					}
					else
					{
						string responsePayload = QUOTE({ "message" : "The value of 'size' should be a string with either 'suspend' or 'resume'." });
						m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
					}
				}
				else
				{
					string responsePayload = QUOTE({ "message" : "Missing 'state' item in payload" });
					m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
				}
			}
			else
			{
				string responsePayload = QUOTE({ "message" : "Failed to parse request payload" });
				m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
			}
		}
		else
		{
			string responsePayload = QUOTE({"status" : "Debugger is not attached to the service" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
		}
	}
	else
	{	string responsePayload = QUOTE({ "status" : "Pipeline debugger features have been disabled" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
	}
}

/**
 * Invoke set debugger step command on the north plugin
 *
 * @param response	The HTTP response
 * @param request	The HTTP request
 */
void NorthApi::stepDebugger(Response response, Request request)
{
	if (m_service->allowDebugger())
	{
		if (m_service->debuggerAttached())
		{
			string payload = request->content.string();
			Document doc;
			ParseResult result = doc.Parse(payload.c_str());
			if (result)
			{
				if (doc.HasMember("steps"))
				{
					if (doc["steps"].IsUint())
					{
						unsigned int steps = doc["steps"].GetUint();
						m_service->stepDebugger(steps);

						string responsePayload = QUOTE({ "status" : "ok" });
						m_service->respond(response, responsePayload);
					}
					else
					{
						string responsePayload = QUOTE({ "message" : "The value of 'steps' should be an unsigned integer" });
						m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
					}
				}
				else
				{
					string responsePayload = QUOTE({ "message" : "Missing 'steps' item in payload" });
					m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
				}
			}
			else
			{
				string responsePayload = QUOTE({ "message" : "Failed to parse request payload" });
				m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
			}
		}
		else
		{
			string responsePayload = QUOTE({"status" : "Debugger is not attached to the service" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
		}
	}
	else
	{	string responsePayload = QUOTE({ "status" : "Pipeline debugger features have been disabled" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
	}
}

/**
 * Invoke debugger replay on the north plugin
 *
 * @param response	The HTTP response
 * @param request	The HTTP request - unused
 */
void NorthApi::replayDebugger(Response response, Request /*request*/)
{
	if (m_service->allowDebugger())
	{
		string responsePayload;
		if (m_service->debuggerAttached())
		{
			// TODO Handle pre-requisites
			m_service->replayDebugger();

			responsePayload = QUOTE({ "status" : "ok" });
		}
		else
		{
			responsePayload = QUOTE({"status" : "Debugger is not attached to the service" });
		}
		m_service->respond(response, responsePayload);
	}
	else
	{	string responsePayload = QUOTE({ "status" : "Pipeline debugger features have been disabled" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
	}
}

/**
 * Invoke debugger state on the north plugin
 *
 * @param response	The HTTP response
 * @param request	The HTTP request - unused
 */
void NorthApi::stateDebugger(Response response, Request /*request*/)
{
	string payload = m_service->debugState();
	m_service->respond(response, payload);
}

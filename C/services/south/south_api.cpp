/**
 * Fledge south service API
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <south_api.h>
#include <south_service.h>
#include <rapidjson/document.h>

using namespace std;
using namespace rapidjson;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

static SouthApi *api = NULL;

/**
 * Wrapper for the PUT setPoint API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void setPointWrapper(shared_ptr<HttpServer::Response> response,
		shared_ptr<HttpServer::Request> request)
{
	if (api)
		api->setPoint(response, request);
}

/**
 * Wrapper for the PUT operation API call
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 */
static void operationWrapper(shared_ptr<HttpServer::Response> response,
		shared_ptr<HttpServer::Request> request)
{
	if (api)
		api->operation(response, request);
}

/**
 * Wrapper for thread creation that is used to start the API
 */
static void startService()
{
	api->startServer();
}

/**
 * South API class constructor
 *
 * @param service	The SouthService class this is the API for
 */
SouthApi::SouthApi(SouthService *service) : m_service(service), m_thread(NULL)
{
	m_logger = Logger::getLogger();
	m_server = new HttpServer();
	m_server->config.port = 0;
	m_server->config.thread_pool_size = 1;

	// AuthenticationMiddleware for PUT regexp paths: use lambda funcion, passing the class object
	m_server->resource[SETPOINT]["PUT"] = [this](shared_ptr<HttpServer::Response> response,
                                                        shared_ptr<HttpServer::Request> request) {
				m_service->AuthenticationMiddlewarePUT(response, request, setPointWrapper);
	};
	m_server->resource[OPERATION]["PUT"] = [this](shared_ptr<HttpServer::Response> response,
                                                        shared_ptr<HttpServer::Request> request) {
				m_service->AuthenticationMiddlewarePUT(response, request, operationWrapper);
	};

	api = this;
	m_thread = new thread(startService);
}

/**
 * Destroy the API.
 *
 * Stop the service and wait fo rthe thread to terminate.
 */
SouthApi::~SouthApi()
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
void SouthApi::startServer()
{
	m_server->start();
}

/**
 * Return the port the service is listening on
 */
unsigned short SouthApi::getListenerPort()
{
	int max_wait = 10;
	// Need to make sure the server thread has started
	while (m_server->getLocalPort() == 0 && max_wait-- > 0)
		usleep(100);
	return m_server->getLocalPort();
}

/**
 * Implement the setPoint PUT request. Caues the write operation on
 * the south plugin to be called with eahc of the set point parameters
 *
 * @param response	The HTTP response
 * @param request	The HTTP request
 */
void SouthApi::setPoint(shared_ptr<HttpServer::Response> response,
			shared_ptr<HttpServer::Request> request)
{
	string payload = request->content.string();
	try {
		Document doc;
		ParseResult result = doc.Parse(payload.c_str());
		if (result)
		{
			if (doc.HasMember("values") && doc["values"].IsObject())
			{
				bool status = true;
				Value& values = doc["values"];
				for (Value::ConstMemberIterator itr = values.MemberBegin();
						itr != values.MemberEnd(); ++itr)
				{
					string name = itr->name.GetString();
					if (itr->value.IsString())
					{
						string value = itr->value.GetString();
						if (!m_service->setPoint(name, value))
						{
							status = false;
						}
					}
				}
				if (status)
				{
					string responsePayload = QUOTE({ "status" : "ok" });
					m_service->respond(response, responsePayload);
				}
				else
				{
					string responsePayload = QUOTE({ "status" : "failed" });
					m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
				}
				return;
			}
			else
			{
				string responsePayload = QUOTE({ "message" : "Missing 'values' object in payload" });
				m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
				return;
			}
		}
		else
		{
			string responsePayload = QUOTE({ "message" : "Failed to parse request payload" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
		}
		
	} catch (exception &e) {
		char buffer[80];
		snprintf(buffer, sizeof(buffer), "\"Exception: %s\"", e.what());
		string responsePayload = QUOTE({ "message" : buffer });
		m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
	}
}

/**
 * Invoke an operation on the south plugin
 *
 * @param response	The HTTP response
 * @param request	The HTTP request
 */
void SouthApi::operation(shared_ptr<HttpServer::Response> response,
			shared_ptr<HttpServer::Request> request)
{
	string payload = request->content.string();
	try {
		Document doc;
		ParseResult result = doc.Parse(payload.c_str());
		if (result)
		{
			string operation;
			if (doc.HasMember("operation") && doc["operation"].IsString())
			{
				operation = doc["operation"].GetString();
				vector<PLUGIN_PARAMETER *> parameters;

				if (doc.HasMember("parameters") && doc["parameters"].IsObject())
				{
					Value& values = doc["parameters"];
					for (Value::ConstMemberIterator itr = values.MemberBegin();
							itr != values.MemberEnd(); ++itr)
					{
						string name = itr->name.GetString();
						if (itr->value.IsString())
						{
							string value = itr->value.GetString();
							PLUGIN_PARAMETER *param = new PLUGIN_PARAMETER;
							param->name = name;
							param->value = value;
							parameters.push_back(param);
						}
					}
				}
				else if (doc.HasMember("parameters"))
				{
					string responsePayload = QUOTE({ "message" : "If present, parameters of an operation must be a JSON object" });
					m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
					return;
				}

				bool status = m_service->operation(operation, parameters);

				for (auto param : parameters)
					delete param;
				if (status)
				{
					string responsePayload = QUOTE({ "status" : "ok" });
					m_service->respond(response, responsePayload);
				}
				else
				{
					string responsePayload = QUOTE({ "status" : "plugin returned failed status for operation" });
					m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
				}
				return;
				
			}
			else
			{
				string responsePayload = QUOTE({ "message" : "Missing 'operation' in payload" });
				m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
				return;
			}
		}
		else
		{
			string responsePayload = QUOTE({ "status" : "failed to parse operation payload" });
			m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
			return;
		}
	} catch (exception &e) {
	}
	string responsePayload = QUOTE({ "status" : "failed" });
	m_service->respond(response, SimpleWeb::StatusCode::client_error_bad_request,responsePayload);
}

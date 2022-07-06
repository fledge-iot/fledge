#include <config_category.h>
#include <string>
#include <management_client.h>
#include <service_handler.h>
#include <config_handler.h>
#include <server_http.hpp>
#include <rapidjson/error/en.h>

#define TO_STRING(...) DEFER(TO_STRING_)(__VA_ARGS__)
#define DEFER(x) x
#define TO_STRING_(...) #__VA_ARGS__
#define QUOTE(...) TO_STRING(__VA_ARGS__)

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

static void bearer_token_refresh_thread(void *data);

/**
 * Initialise m_mgtClient object to NULL
 */
ManagementClient *ServiceAuthHandler::m_mgtClient = NULL;

/**
 * Create "${service}Security" category with empty content
 *
 * @param mgtClient	The management client object
 * @return		True on success, False otherwise
 */
bool ServiceAuthHandler::createSecurityCategories(ManagementClient* mgtClient)
{
	string securityCatName = m_name + string("Security");
	DefaultConfigCategory defConfigSecurity(securityCatName, string("{}"));

	// All services add 'AuthenticatedCaller' item
	// Add AuthenticatedCaller item, set to "false"
	defConfigSecurity.addItem("AuthenticatedCaller",
				"Security config params",
				"boolean",
				"false",
				"false");
	defConfigSecurity.setItemDisplayName("AuthenticatedCaller",
				"Enable caller authorisation");

	// Create/Update category name (we pass keep_original_items=true)
	mgtClient->addCategory(defConfigSecurity, true);

	// Add this service under 'm_name' parent category
	vector<string> children1;
	children1.push_back(securityCatName);
	mgtClient->addChildCategories(m_name, children1);

	// Get new or merged category content
	m_security = mgtClient->getCategory(m_name + "Security");

	this->setInitialAuthenticatedCaller();

	// Register for security category content changes
	ConfigHandler *configHandler = ConfigHandler::getInstance(mgtClient);
	if (configHandler == NULL)
	{
		Logger::getLogger()->error("Failed to get access to ConfigHandler for %s",
					m_name.c_str());
		return false;
	}

	// Register for content change notification
	configHandler->registerCategory(this, m_name + "Security");

	// Start thread for automatic bearer token refresh, before expiration
	if (this->getType() != "Southbound")
	{
		new thread(bearer_token_refresh_thread, this);
	}

	return true;
}

/**
 * Update the class objects from security category content update
 *
 * @param category	The service category name
 * @return		True on success, False otherwise
 */
 
bool ServiceAuthHandler::updateSecurityCategory(const string& category)
{
	// Lock config
	lock_guard<mutex> cfgLock(m_mtx_config);

	m_security = ConfigCategory(m_name + "Security", category);
	bool acl_set = false;
	// Check for AuthenticatedCaller main switch
	if (m_security.itemExists("AuthenticatedCaller"))
	{
		string val = m_security.getValue("AuthenticatedCaller");
		if (val[0] == 't' || val[0] == 'T')
		{
			acl_set = true;
		}
	}

	m_authentication_enabled = acl_set;

	Logger::getLogger()->debug("updateSecurityCategory called, switch val %d", acl_set);

	return acl_set;
}

/**
 * Set initial value of enabled authentication
 */
void ServiceAuthHandler::setInitialAuthenticatedCaller()
{
	bool acl_set = false;
	if (m_security.itemExists("AuthenticatedCaller"))
	{
		string val = m_security.getValue("AuthenticatedCaller");
		Logger::getLogger()->debug("This service '%s' has AuthenticatedCaller item %s",
			m_name.c_str(),
			val.c_str());
		if (val[0] == 't' || val[0] == 'T')
		{
			acl_set = true;
		}
		this->setAuthenticatedCaller(acl_set);
	}
}

/**
 * Set enabled authentication value
 *
 * @param enabled	The enable/disable flag to set
 */
void ServiceAuthHandler::setAuthenticatedCaller(bool enabled)
{
	lock_guard<mutex> guard(m_mtx_config);
	m_authentication_enabled = enabled;
}

/**
 * Return enabled authentication value
 *
 * @return	True on success, False otherwise
 */
bool ServiceAuthHandler::getAuthenticatedCaller()
{
	lock_guard<mutex> guard(m_mtx_config);
	return m_authentication_enabled;
}

/**
 * Verify URL path against URL array in security configuration
 * If array item value has ACL property a service name/type check is added
 *
 * @param   path	The requested service HTTP resource
 * @param   serviceName	The serviceName to check
 * @param   serviceType	The serviceType to check
 * @return		True is the resource acces has been granted, false otherwise
 */
bool ServiceAuthHandler::verifyURL(const string& path,
				const string& serviceName,
				const string& serviceType)
{
	Document doc;
 
	// Parse security config with lock
	unique_lock<mutex> cfgLock(m_mtx_config);

	string acl;
	if (this->m_security.itemExists("ACL"))
	{
		acl = this->m_security.getValue("ACL");
	}
	cfgLock.unlock();

	if (acl.empty())
	{
		return true;
	}

	doc.Parse(acl.c_str());

	// Check
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("Failed to parse ACL JSON data: %s. Document is %s",
				GetParseError_En(doc.GetParseError()),
				acl.c_str());
		return false;
	}

	Value arrayURL;
	if (!this->m_security.itemExists("url"))
	{
		return true;
	}

	if (!doc["url"].IsArray())
	{
		return false;
	}

	arrayURL = doc["url"];
	if (arrayURL.Size() == 0)
	{
		return true;
	}

	if (arrayURL.Size() > 0)
	{
		bool typeMatched = false;
		bool URLMatched = false;

		for (Value::ConstValueIterator it = arrayURL.Begin();
		     it != arrayURL.End();
		     ++it)

		{
			if (it->IsObject())
			{
				if (it->HasMember("url") && (*it)["url"].IsString())
				{
					string configURL = (*it)["url"].GetString();
					// Request path matches configured URLs
					if (configURL != "" && configURL == path)
					{
						URLMatched = true;
					}
				}
				if (URLMatched)
				{
					if (it->HasMember("acl") && (*it)["acl"].IsArray())
					{
						auto arrayServices = (*it)["acl"].GetArray();
						if (arrayServices.Size() == 0)
						{
							return true;
						}
						for (Value::ConstValueIterator iS = arrayServices.Begin();
									     iS != arrayServices.End();
									     ++iS)
						{
							if (iS->IsObject())
							{
								if (iS->HasMember("type") &&
								    (*iS)["type"].IsString())
								{
									string type = (*iS)["type"].GetString();
									if (type == serviceType)
									{
										typeMatched = true;
										break;
									}
								}
							}
						}
					}
				}
			}
		}

		Logger::getLogger()->debug("verify URL path '%s', type '%s': "
					"result URL %d, result type %d",
					path.c_str(),
					serviceType.c_str(),
					URLMatched,
					typeMatched);

		return URLMatched == true || typeMatched == true;
	}

	return false;
}

/**
 * Verify service caller name and type against ACL array in security configuration
 *
 * @param   sName	The caller service name
 * @param   sType	The caller service type (Northbound, Southbound, Notification, etc)
 * @return		True is the resource acces has been granted, false otherwise
 */
bool ServiceAuthHandler::verifyService(const string& sName, const string &sType)
{
	// Check m_security category item ACL value service array
	Document doc;
	Value arrayService;

	// Parse security config with lock
	unique_lock<mutex> cfgLock(m_mtx_config);

	string acl;
	if (this->m_security.itemExists("ACL"))
	{
		acl = this->m_security.getValue("ACL");
	}
	cfgLock.unlock();

	if (acl.empty())
	{
		Logger::getLogger()->debug("verifyService '%s', type '%s', "
					"the ACL is not set: allow any service",
					sName.c_str(),
					sType.c_str());
		return true;
	}

	doc.Parse(acl.c_str());

	// Check
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("Failed to parse ACL JSON data: %s. Document is %s",
				GetParseError_En(doc.GetParseError()),
				acl.c_str());
		return false;
	}
	if (!doc["service"].IsArray())
	{
		Logger::getLogger()->error("verifyService '%s', type '%s', in ACL '%s' "
					", 'service' item is not an array",
					sName.c_str(),
					sType.c_str(),
					acl.c_str());
		return false;
	}

	arrayService = doc["service"];
	if (arrayService.Size() == 0)
	{
		Logger::getLogger()->debug("verifyService '%s', type '%s', in ACL 'service' "
					"item is empty: allow any service",
					sName.c_str(),
					sType.c_str());
		return true;
	}

	if (arrayService.Size() > 0)
	{
		bool serviceMatched = false;
		bool typeMatched = false;

		for (Value::ConstValueIterator it = arrayService.Begin();
		     it != arrayService.End();
		     ++it)

		{
			if (it->IsObject())
			{
				if (it->HasMember("name") &&
				    (*it)["name"].IsString())
				{
					string name = (*it)["name"].GetString();
					if (name == sName)
					{
						serviceMatched = true;
						break;
					}
				}

				if (it->HasMember("type") &&
				    (*it)["type"].IsString())
				{
					string type = (*it)["type"].GetString();
					if (type == sType)
					{
						typeMatched = true;
						break;
					}
				}
			}
		}

		Logger::getLogger()->debug("verify service '%s', type '%s': "
					"result service %d, result type %d",
					sName.c_str(),
					sType.c_str(),
					serviceMatched,
					typeMatched);

		return serviceMatched == true || typeMatched == true;
	}

	return false;
}

/**
 * Authentication Middleware for PUT methods
 *
 * Routine first check whether the service is configured with authentication
 *
 * Access bearer token is then verified against FogLAMP core API endpoint
 * JWT token claims are passed to verifyURL and verifyService routines
 *
 * If access is granted the input funcPUT funcion is called
 * otherwise error response is sent to the client
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 * @param funcPUT	The function to call in case of access granted
 */
void ServiceAuthHandler::AuthenticationMiddlewarePUT(shared_ptr<HttpServer::Response> response,
				shared_ptr<HttpServer::Request> request,
        			std::function<void(
        		        shared_ptr<HttpServer::Response>,
        		        shared_ptr<HttpServer::Request>)> funcPUT)
{
	string callerName;
	string callerType;

	for(auto &field : request->header)
	{
		if (field.first == "Service-Orig-From")
		{
			callerName = field.second;
		}
		if (field.first == "Service-Orig-Type")
		{
			callerType = field.second;
		}
	}

	// Get authentication enabled value
	bool acl_set = this->getAuthenticatedCaller();
	Logger::getLogger()->debug("This service '%s' has AuthenticatedCaller flag set %d "
			"caller service is %s, type %s",
			this->getName().c_str(),
			acl_set,
			callerName.c_str(),
			callerType.c_str());

	// Check authentication
	if (acl_set)
	{
		// Verify token via Fledge management core POST API call
		// we do not need token claims here
		bool ret = m_mgtClient->verifyAccessBearerToken(request);
		if (!ret)
		{
			string msg = "invalid service bearer token";
			string responsePayload = "{ \"error\" : \"" + msg + "\" }";
			Logger::getLogger()->error(msg.c_str());
			this->respond(response,
					SimpleWeb::StatusCode::client_error_bad_request,
					responsePayload);

			return;
		}

		// Check whether caller name and type are passed
		if (callerName.empty() && callerType.empty())
		{
			string msg = "authorisation not granted " \
				"to this service: missing caller name and type";
			string responsePayload = "{ \"error\" : \"" + msg + "\" }";
			Logger::getLogger()->error(msg.c_str());

			this->respond(response,
					SimpleWeb::StatusCode::client_error_unauthorized,
					responsePayload);
			return;
		}

		// Dispatcher service is always allowed to send control requests
		// to south service
		//
		// Checking for valid origin service caller (name/type) i.e
		// N1_HTTP/Northbound
		// NOTS/Notification
		bool valid_service = this->verifyService(callerName, callerType);
		if (!valid_service)
		{
			string msg = "authorisation not granted to this service";
			string responsePayload = "{ \"error\" : \"" + msg + "\" }";
			Logger::getLogger()->error(msg.c_str());
			this->respond(response,
					SimpleWeb::StatusCode::client_error_unauthorized,
					responsePayload);
			return;
		}

		// Check URLS
		bool access_granted = this->verifyURL(request->path,
						callerName,
						callerType);
		if (!access_granted)
		{
			string msg = "authorisation not granted to this resource";
			string responsePayload = "{ \"error\" : \"" + msg + "\" }";
			Logger::getLogger()->error(msg.c_str());
			this->respond(response,
					SimpleWeb::StatusCode::client_error_unauthorized,
					responsePayload);
			return;
		}
	}

	// Call PUT endpoint routine
	funcPUT(response, request);
}

/**
 * Authentication Middleware ACL check
 *
 * serviceName, serviceType and url (request->path)
 * are cheked with verifyURL and verifyService routines
 *
 * If access is granted return true
 * otherwise error response is sent to the client and return is false
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 * @param callerName	The caller service name to check
 * @param callerType	The caller service type to check
 * @return		True on success
 * 			False otherwise with server reply error
 */
bool ServiceAuthHandler::AuthenticationMiddlewareACL(shared_ptr<HttpServer::Response> response,
						shared_ptr<HttpServer::Request> request,
						const string& callerName,
						const string& callerType)
{
	// Check for valid service caller (name, type)
	bool valid_service = this->verifyService(callerName, callerType);
	if (!valid_service)
	{
		string msg = "authorisation not granted to this service";
		string responsePayload = "{ \"error\" : \"" + msg + "\" }";
		Logger::getLogger()->error(msg.c_str());

		// Error reply to client
		this->respond(response,
				SimpleWeb::StatusCode::client_error_unauthorized,
				responsePayload);
		return false;
	}

	// Check URLS
	bool access_granted = this->verifyURL(request->path, callerName, callerType);
	if (!access_granted)
	{
		string msg = "authorisation not granted to this resource";
		string responsePayload = "{ \"error\" : \"" + msg + "\" }";
		Logger::getLogger()->error(msg.c_str());

		// Error reply to client
		this->respond(response,
				SimpleWeb::StatusCode::client_error_unauthorized,
				responsePayload);
		return false;
	}

	return true;
}

/**
 * Authentication Middleware for Dispatcher service
 *
 * Routine first check whether the service is configured with authentication
 *
 * Access bearer token is then verified against FogLAMP core API endpoint
 * token claims 'sub' and 'aud' along with request are passed to
 * verifyURL and verifyService routines
 *
 * If access is granted then return map with token claims 
 * otherwise error response is sent to the client
 * and empty map is returned.
 *
 * @param response	The HTTP Response to send
 * @param request	The HTTP Request
 * @return		True on success
 *			False on errors
 */
bool ServiceAuthHandler::AuthenticationMiddlewareCommon(shared_ptr<HttpServer::Response> response,
							shared_ptr<HttpServer::Request> request,
							string& callerName,
							string& callerType)
{
	// Get token from HTTP request
	BearerToken bToken(request);

	// Verify token via Fledge management core POST API call and fill tokenClaims map
	bool ret = m_mgtClient->verifyAccessBearerToken(bToken);
	if (!ret)
	{
		string msg = "invalid service bearer token";
		string responsePayload = "{ \"error\" : \"" + msg + "\" }";
		Logger::getLogger()->error(msg.c_str());

		// Error reply to client
		this->respond(response,
				SimpleWeb::StatusCode::client_error_bad_request,
				responsePayload);

		// Failure
		return false;
	}

	// Check for valid service caller (name, type) and URLs
	bool check = this->AuthenticationMiddlewareACL(response,
						request,
						bToken.getSubject(),
						bToken.getAudience());
	// Check ACL result
	if (!check)
	{
		// Failure
		return false;
	}

	// Set caller name & type
	callerName = bToken.getSubject();
	callerType = bToken.getAudience();

	// Success
	return true;
}

/**
 * Refresh the bearer token of the runnign service
 * This routine is run by a thread started in
 * createSecurityCategories.
 *
 * After sleep time got in 'exp' of curren token
 * a new one is requested to the core via
 * token_refresh API endpoint
 */
void ServiceAuthHandler::refreshBearerToken()
{
	Logger::getLogger()->debug("Bearer token refresh thread starts for service '%s'",
				this->getName().c_str());

	int max_retries = 2;
	time_t expires_in;
	int k = 0;

	// While server is running get bearer token
	// and sleeps for expires_in - 10 seconds
	// then get new token and sleep again
	while (this->isRunning())
	{
		if (k >= max_retries)
		{
			string msg = "Bearer token not found for service '" + this->getName() +
					" refresh thread exits after " + std::to_string(max_retries) + " retries";	
			Logger::getLogger()->error(msg.c_str());
			throw std::runtime_error(msg);
		}

		bool tokenVerified = false;
		// Fetch current bearer token
		BearerToken bToken(m_mgtClient->getRegistrationBearerToken());
		if (bToken.exists())
		{
			// Ask verification to core service nad get token claims
			tokenVerified = m_mgtClient->verifyBearerToken(bToken);

		}

		// Give it a try in case of any error from core service
		if (!tokenVerified)
		{
			k++;
			Logger::getLogger()->error("Refreshing bearer token thread for service '%s' "
						"got empty or invalid bearer token '%s', retry n. %d",
						this->getName().c_str(),
						bToken.token().c_str(),
						k);

			// Sleep for some time
			std::this_thread::sleep_for(std::chrono::seconds(30));

			continue;
		}

		// Token exists and it is valid, get expiration time
		expires_in = bToken.getExpiration() - time(NULL) - 10;

		Logger::getLogger()->debug("Bearer token refresh thread sleeps "
					"for %ld seconds, service '%s'",
					expires_in,
					this->getName().c_str());

		// Thread sleeps for the given amount of time
		std::this_thread::sleep_for(std::chrono::seconds(expires_in));

		Logger::getLogger()->debug("Bearer token refresh thread calls "
					"token refresh endpoint for service '%s'",
					this->getName().c_str());

		// Get a new bearer token for this service via
		// refresh_token core API endpoint
		string newToken;
		bool ret = m_mgtClient->refreshBearerToken(bToken.token(), newToken);
		if (ret)
		{
			Logger::getLogger()->debug("Bearer token refresh thread has got "
					"a new bearer token for service '%s, %s",
					this->getName().c_str(),
					newToken.c_str());

			// Store new bearer token
			m_mgtClient->setNewBearerToken(newToken);
		}
		else
		{
			string msg = "Failed to get a new token "
				"via refresh API call for service '" + this->getName() + "'";
			Logger::getLogger()->fatal("%s, current token is '%s'",
					msg.c_str(),
					bToken.token().c_str());
			throw std::runtime_error(msg);
		}
	}

	Logger::getLogger()->info("Refreshing bearer token thread for service '%s' stopped",
				this->getName().c_str());
}

/**
 * Thread to refresh the bearer token for
 *
 * @param data	Pointer to ServiceAuthHandler object
 */
static void bearer_token_refresh_thread(void *data)
{
	ServiceAuthHandler *service = (ServiceAuthHandler *)data;
	service->refreshBearerToken();
}

/**
 * Request security change action:
 *
 * Given a reason code, “attachACL”, “detachACL”, “reloadACL”
 * in 'reason' atribute, the ACL name in 'argument' could be
 * attached, detached or reloaded
 */
void ServiceAuthHandler::securityChange(const string& payload)
{
	Logger::getLogger()->debug("securityChange called for %s: %s",
				this->getName().c_str(),
				payload.c_str());
	// TODO load, reload or detach ACL
}

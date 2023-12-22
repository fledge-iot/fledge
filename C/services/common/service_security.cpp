#include <config_category.h>
#include <string>
#include <management_client.h>
#include <service_handler.h>
#include <config_handler.h>
#include <server_http.hpp>
#include <rapidjson/error/en.h>
#include <acl.h>

#define TO_STRING(...) DEFER(TO_STRING_)(__VA_ARGS__)
#define DEFER(x) x
#define TO_STRING_(...) #__VA_ARGS__
#define QUOTE(...) TO_STRING(__VA_ARGS__)

#define DELTA_SECONDS_BEFORE_TOKEN_EXPIRATION 120

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

/**
 * Initialise m_mgtClient object to NULL
 */
ManagementClient *ServiceAuthHandler::m_mgtClient = NULL;

/**
 * Create "${service}Security" category with empty content
 *
 * @param mgtClient	The management client object
 * @param dryRun	Dryrun so do not register interest in the category
 * @return		True on success, False otherwise
 */
bool ServiceAuthHandler::createSecurityCategories(ManagementClient* mgtClient, bool dryRun)
{
	string securityCatName = m_name + string("Security");
	DefaultConfigCategory defConfigSecurity(securityCatName, string("{}"));

	// All services add 'AuthenticatedCaller' item
	// Add AuthenticatedCaller item, set to "false"
	defConfigSecurity.addItem("AuthenticatedCaller",
				"Security enable parameter",
				"boolean",
				// For dispatcher set default = true
				this->getType() == "Dispatcher" ? "true" : "false", // Default
				"false"); // Value
	defConfigSecurity.setItemDisplayName("AuthenticatedCaller",
				"Enable caller authorisation");

	defConfigSecurity.addItem("ACL",
				"Service ACL for " + m_name,
				"ACL",
				"",  // Default
				""); // Value
	defConfigSecurity.setItemDisplayName("ACL",
				"Service ACL");

	defConfigSecurity.setDescription(m_name + " Security");

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

	if (!dryRun)
	{
		// Register for content change notification
		configHandler->registerCategory(this, m_name + "Security");
	}

	// Load ACL given the value of 'acl' type item: i.e.
	string acl_name = m_security.getValue("ACL");
	if (!acl_name.empty())
	{
		m_service_acl = m_mgtClient->getACL(acl_name);
	}

	// Start housekeeper task for automatic bearer token refresh, before expiration
	if (this->getType() != "Southbound" && dryRun == false)
	{
		m_refreshTask = new BearerTokenRefresh(this);
		HouseKeeper::getInstance()->addTask(m_refreshTask);
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

	// Note: as per FOGL-6612
	// Only AuthenticatedCaller will be handled in Security category change notification
	// ACL update is made via security change service handler 
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
	// Check config with lock
	unique_lock<mutex> cfgLock(m_mtx_config);

	// Check m_security category item ACL is set
	string acl;
	if (this->m_security.itemExists("ACL"))
	{
		acl = this->m_security.getValue("ACL");
	}
	cfgLock.unlock();

	if (acl.empty())
	{
		Logger::getLogger()->debug("verifyURL '%s', type '%s', "
					"the ACL is not set: allow any URL from any service type",
					serviceName.c_str(),
					serviceType.c_str());
		return true;
	}

	const vector<ACL::UrlItem>& arrayURL = this->m_service_acl.getURL();
	if (arrayURL.size() == 0)
	{
		Logger::getLogger()->debug("verifyURL '%s', type '%s', "
					"the URL array is empty: allow any URL from any service type",
					serviceName.c_str(),
					serviceType.c_str());
		return true;
	}

	if (arrayURL.size() > 0)
	{
		bool typeMatched = false;
		bool URLMatched = false;

		// Check URL value
		for (auto it = arrayURL.begin(); it != arrayURL.end(); ++it)
		{
			string configURL = (*it).url;
			// Request path matches configured URLs
			if (configURL != "" && configURL == path)
			{
				URLMatched = true;
			}

			vector<ACL::KeyValueItem> aclServices = (*it).acl;
			if (URLMatched && aclServices.size() == 0)
			{
				Logger::getLogger()->debug("verifyURL '%s', type '%s', "
					"the URL '%s' has no ACL : allow any service type",
					serviceName.c_str(),
					serviceType.c_str());
				return true;
			}
			for (auto iS = aclServices.begin();
			    	  iS != aclServices.end();
				  ++iS)
			{
				if ((*iS).key == "type" && (*iS).value == serviceType)
				{
					typeMatched = true;
					break;
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
	// Check config with lock
	unique_lock<mutex> cfgLock(m_mtx_config);

	// Check m_security category item ACL is set
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

	vector<ACL::KeyValueItem> aclServices = this->m_service_acl.getService();
	if (aclServices.size() == 0)
	{
		Logger::getLogger()->debug("verifyService '%s', type '%s', " \
					"has an empty ACL service array: allow any service",
					sName.c_str(),
					sType.c_str());
		return true;
	}

	if (aclServices.size() > 0)
	{
		bool serviceMatched = false;
		bool typeMatched = false;

		for (auto it = aclServices.begin(); it != aclServices.end(); ++it)
		{
			if ((*it).key == "name" && (*it).value == sName)
			{
				serviceMatched = true;
				break;
			}
			if ((*it).key == "type" && (*it).value == sType)
			{
				typeMatched = true;
				break;
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
 * Refresh the bearer token of the running service
 * This routine is run by the housekeeper on a fixed schedule
 *
 * a new one is requested to the core via
 * token_refresh API endpoint
 */
void ServiceAuthHandler::refreshBearerToken()
{
	string currentToken;
	time_t expiry = 0;
	// Fetch current bearer token
	BearerToken bToken(m_mgtClient->getRegistrationBearerToken());
	if (bToken.exists() && m_mgtClient->verifyBearerToken(bToken))
	{
		// We have a verified bearer token
		currentToken = bToken.token();
		expiry = bToken.getExpiration();
	}
	else
	{
		if (k >= max_retries)
		{
			string msg = "Bearer token not found for service '" + this->getName() +
					" refresh thread exits after " + std::to_string(max_retries) + " retries";	
			Logger::getLogger()->error(msg.c_str());

			// Shutdown service
			if (m_refreshRunning)
			{
				Logger::getLogger()->warn("Service is being restarted " \
						"due to bearer token refresh error");
				this->restart();
				break;
			}
		}

		if (!tokenVerified)
		{
			// Fetch current bearer token
			BearerToken bToken(m_mgtClient->getRegistrationBearerToken());
			if (bToken.exists() && m_mgtClient->verifyBearerToken(bToken))
			{
				currentToken = bToken.token();
				expiry = bToken.getExpiration();
			}
	}
	if (expiry < time(0))
	{
		// We have gone beyond token expiry - restart the service
		Logger::getLogger()->warn("Bearer token has expired, forcing a restart of the service");
		this->restart();
	}
	else if (expiry - time(0) < REFRESH_CHECK_INTERVAL * 3)
	{
		string newToken;
		bool ret = m_mgtClient->refreshBearerToken(currentToken, newToken);
		if (ret)
		{
			Logger::getLogger()->debug("Bearer token has been refreshed %s",
					newToken.c_str());

			// Store new bearer token
			m_mgtClient->setNewBearerToken(newToken);
		}
		else
		{
			Logger::getLogger()->warn("Refresh of the service bearer token has failed.");
		}
	}
}

/**
 * Request security change action:
 *
 * Given a reason code, “attachACL”, “detachACL”, “reloadACL”, “updateACL”
 * in 'reason' atribute, the ACL name in 'argument' could be
 * attached, detached or reloaded
 *
 * @param payload	The JSON document with 'reason' and 'argument' 
 * @retun 		True on success
 */
bool ServiceAuthHandler::securityChange(const string& payload)
{
	// Parse JSON data
	ACL::ACLReason reason(payload);

	Logger::getLogger()->debug("Reason is %s, argument %s",
				reason.getReason().c_str(),
				reason.getArgument().c_str());

	string r = reason.getReason();

	// Lock config
	lock_guard<mutex> cfgLock(m_mtx_config);

	if (r == "attachACL")
	{
		// Fetch and load ACL
		m_service_acl = m_mgtClient->getACL(reason.getArgument());
	}
	else if (r == "reloadACL" || r == "updateACL")
	{
		// Fetch and load new or updated ACL
		m_service_acl = m_mgtClient->getACL(reason.getArgument());
	}
	else if (r == "detachACL")
	{
		m_service_acl = ACL();
	}
	else
	{
		// Error
		Logger::getLogger()->error("Reason '%s' is not supported",
					reason.getReason().c_str());
		return false;
	}

	return true;
}

/**
 * Housekeeper task execution.
 *
 * Refresh the bearer token
 */
void BearerTokenRefresh::run()
{
	m_handler->refreshBearerToken();
}


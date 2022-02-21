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

	defConfigSecurity.setDescription(m_name + string(" security config params"));

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
	if (this->getAuthenticatedCaller())
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
		Logger::getLogger()->debug("This service %s has AuthenticatedCaller item %s",
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
	if (!doc["URL"].IsArray())
	{
		return false;
	}

	arrayURL = doc["URL"];
	if (arrayURL.Size() == 0)
	{
		return true;
	}

	if (arrayURL.Size() > 0)
	{
		bool serviceMatched = false;
		bool typeMatched = false;

		for (Value::ConstValueIterator it = arrayURL.Begin();
		     it != arrayURL.End();
		     ++it)

		{
			if (it->IsObject() &&
			    (it->HasMember("URL") &&
			    (*it)["URL"].IsString()))
			{
				string configURL = (*it)["URL"].GetString();
				// Request path matches configured URLs
				if (configURL == path)
				{
					// Check whether there is a service ACL for the matched URL
					return this->verifyService(serviceName, serviceType);
				}
			}
		}
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
		return false;
	}

	arrayService = doc["service"];
	if (arrayService.Size() == 0)
	{
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

	string serviceName;
	string serviceType;

	for(auto &field : request->header)
	{
		if (field.first == "Service-Orig-From")
		{
			serviceName = field.second;
		}
		if (field.first == "Service-Orig-Type")
		{
			serviceType = field.second;
		}
	}

	// Get authentication enabled value
	bool acl_set = this->getAuthenticatedCaller();
	Logger::getLogger()->debug("This service %s has AuthenticatedCaller flag set %d",
			this->getName().c_str(),
			acl_set);

	// Check authentication
	if (acl_set)
	{
		map<string, string> tokenClaims;
		// Verify token via Fledge management core POST API call
		// and fill tokenClaims map
		bool ret = m_mgtClient->verifyAccessBearerToken(request, tokenClaims);
		if (!ret)
		{
			string responsePayload = QUOTE({ "error" : "invalid service bearer token"});
			Logger::getLogger()->error("invalid service bearer token");
			this->respond(response,
					SimpleWeb::StatusCode::client_error_bad_request,
					responsePayload);

			return;
		}

		// Check for valid service caller (name, type)
		bool valid_service = this->verifyService(serviceName, serviceType);
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
						serviceName,
						serviceType);
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
 * Authentication Middleware for POST methods
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
void ServiceAuthHandler::AuthenticationMiddlewarePOST(shared_ptr<HttpServer::Response> response,
			shared_ptr<HttpServer::Request> request,
			std::function<void(
				shared_ptr<HttpServer::Response>,
				shared_ptr<HttpServer::Request>)> funcPOST)
{
	// POST does not have additional features, call PUT method
	// passing pinter to POST function
	this->AuthenticationMiddlewarePUT(response, request, funcPOST);
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
 * @param serviceName	The service name to check
 * @param serviceType	The service type to check
 * @return		True on success
 *			False otherwise with server reply error
 */
bool ServiceAuthHandler::AuthenticationMiddlewareACL(shared_ptr<HttpServer::Response> response,
						shared_ptr<HttpServer::Request> request,
						const string& serviceName,
						const string& serviceType)
{
	// Check for valid service caller (name, type)
	bool valid_service = this->verifyService(serviceName, serviceType);
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
	bool access_granted = this->verifyURL(request->path, serviceName, serviceType);
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
 * @return		Map with token claims on success
 *			empty map in case of errors
 */
map<string, string>
	ServiceAuthHandler::AuthenticationMiddlewareCommon(shared_ptr<HttpServer::Response> response,
							shared_ptr<HttpServer::Request> request)
{
	// Verify token via Fledge management core POST API call and fill tokenClaims map
	map<string, string> tokenClaims;
	bool ret = m_mgtClient->verifyAccessBearerToken(request, tokenClaims);
	if (!ret)
	{
		string msg = "invalid service bearer token";
		string responsePayload = "{ \"error\" : \"" + msg + "\" }";
		Logger::getLogger()->error(msg.c_str());

		// Error reply to client
		this->respond(response,
				SimpleWeb::StatusCode::client_error_bad_request,
				responsePayload);

		// Return emptyClaims
		map<string, string> emptyClaims;
		return emptyClaims;
	}

	// Check for valid service caller (name, type) and URLs
	bool auth = this->AuthenticationMiddlewareACL(response,
						request,
						tokenClaims["sub"],
						tokenClaims["aud"]);
	// Check
	if (!auth)
	{
		// Return emptyClaims
		map<string, string> emptyClaims;
		return emptyClaims;
	}

	// Return tokenClaims from bearer token
	return tokenClaims;
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
	map<string, string> claims;
	time_t expires_in;
	string bToken;
	int k = 0;

	// While server is running get bearer token
	// and sleeps for expires_in - 10 seconds
	// then get new token and sleep again
	while (this->isRunning())
	{
		if (k >= max_retries)
		{
			Logger::getLogger()->error("Bearer token not found for service %s, "
						"refresh thread stops after %d retries",
						this->getName().c_str(),
						max_retries);
			break;
		}

		bool tokenExists = false;
		// Fetch current bearer token
		bToken = m_mgtClient->getRegistrationBearerToken();
		if (bToken != "")
		{
			// Ask verification to core service nad get token claims
			m_mgtClient->verifyBearerToken(bToken, claims);

			// 'sub', 'aud', 'iss', 'exp'
			tokenExists = claims.size() == 4;
		}

		// Give it a try in case of any error from core service
		if (!tokenExists)
		{
			k++;
			Logger::getLogger()->error("Refreshing bearer token thread for service '%s' "
						"got empty or invalid bearer token '%s', retry n. %d",
						this->getName().c_str(),
						bToken.c_str(),
						k);

			// Sleep for some time
			std::this_thread::sleep_for(std::chrono::seconds(30));

			continue;
		}

		// Token exists and it is valid, get expiration time
		expires_in = std::stoi(claims["exp"]) - time(NULL) - 10;

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
		string newToken = m_mgtClient->refreshBearerToken(bToken);
		if (newToken != "")
		{
			Logger::getLogger()->debug("Bearer token refresh thread has got "
						"a new bearer token for service '%s",
						this->getName().c_str());

			// Store new bearer token
			m_mgtClient->setNewBearerToken(newToken);
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

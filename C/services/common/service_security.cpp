#include <config_category.h>
#include <string>
#include <management_client.h>
#include <service_handler.h>
#include <config_handler.h>
#include <server_http.hpp>

#define TO_STRING(...) DEFER(TO_STRING_)(__VA_ARGS__)
#define DEFER(x) x
#define TO_STRING_(...) #__VA_ARGS__
#define QUOTE(...) TO_STRING(__VA_ARGS__)

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
		return false;
	}

	// Register for content change notification
	configHandler->registerCategory(this, m_name + "Security");

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
 * @param   claims	JWT bearer token claims
 * @return		True is the resource acces has been granted, false otherwise
 */
bool ServiceAuthHandler::verifyURL(const string& path, map<string, string> claims)
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

	Value arrayURL;
	if (doc["URL"].IsArray())
	{
		arrayURL = doc["URL"];
	}
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
					return this->verifyService(claims["sub"], claims["aud"]);
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
bool ServiceAuthHandler::verifyService(string& sName, string &sType)
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

	if (doc["service"].IsArray())
	{
		arrayService = doc["service"];
	}

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
	// Get authentication enabled value
	bool acl_set = this->getAuthenticatedCaller();

	// Check authentication
	if (acl_set)
	{
		Logger::getLogger()->debug("This service %s has AuthenticatedCaller flag set %d",
			this->getName().c_str(),
			acl_set);
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
		bool valid_service = this->verifyService(tokenClaims["sub"], tokenClaims["aud"]);
		if (!valid_service)
		{
			string msg = "authorisation not granted to this service";
			string responsePayload = "{ \"error\" : \"" + msg + "\" }";
			Logger::getLogger()->error(msg);
			this->respond(response,
					SimpleWeb::StatusCode::client_error_unauthorized,
					responsePayload);
			return;
		}

		// Check URLS
		bool access_granted = this->verifyURL(request->path, tokenClaims);
		if (!access_granted)
		{
			string responsePayload = QUOTE({ "error" : "authorisation not granted to this resource"});
			this->respond(response,
					SimpleWeb::StatusCode::client_error_unauthorized,
					responsePayload);
			return;
		}
	}

	// Call PUT endpoint routine
	funcPUT(response, request);
}

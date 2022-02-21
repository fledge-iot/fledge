/*
 * Fledge storage service.
 *
 * Copyright (c) 2017-2021 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <management_client.h>
#include <rapidjson/document.h>
#include <service_record.h>
#include <string_utils.h>
#include <asset_tracking.h>
#include <bearer_token.h>
#include <crypto.hpp>
#include <rapidjson/error/en.h>

using namespace std;
using namespace rapidjson;
using namespace SimpleWeb;
using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

/**
 * Management Client constructor. Creates a class used to send management API requests
 * from a micro service to the Fledge core service.
 *
 * The parameters required here are passed to new services and tasks using the --address=
 * and --port= arguments when the service is started.
 *
 * @param hostname	The hostname of the Fledge core micro service
 * @param port		The port of the management service API listener in the Fledge core
 */
ManagementClient::ManagementClient(const string& hostname, const unsigned short port) : m_uuid(0)
{
ostringstream urlbase;

	m_logger = Logger::getLogger();
	m_urlbase << hostname << ":" << port;
}

/**
 * Destructor for management client
 */
ManagementClient::~ManagementClient()
{
	std::map<std::thread::id, HttpClient *>::iterator item;

	if (m_uuid)
	{
		delete m_uuid;
		m_uuid = 0;
	}

	// Deletes all the HttpClient objects created in the map
	for (item  = m_client_map.begin() ; item  != m_client_map.end() ; ++item)
	{
		delete item->second;
	}
}

/**
 * Creates a HttpClient object for each thread
 * it stores/retrieves the reference to the HttpClient and the associated thread id in a map
 *
 * @return HttpClient	The HTTP client connection to the core
 */
HttpClient *ManagementClient::getHttpClient() {

	std::map<std::thread::id, HttpClient *>::iterator item;
	HttpClient *client;

	std::thread::id thread_id = std::this_thread::get_id();

	m_mtx_client_map.lock();
	item = m_client_map.find(thread_id);

	if (item  == m_client_map.end() ) {

		// Adding a new HttpClient
		client = new HttpClient(m_urlbase.str());
		m_client_map[thread_id] = client;
	}
	else
	{
		client = item->second;
	}

	m_mtx_client_map.unlock();

	return (client);
}

/**
 * Register this service with the Fledge core
 *
 * @param service	The service record of this service
 * @return bool		True if the service registration was sucessful
 */
bool ManagementClient::registerService(const ServiceRecord& service)
{
string payload;

	try {
		service.asJSON(payload);

		auto res = this->getHttpClient()->request("POST", "/fledge/service", payload);
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) &&
					  isdigit(response[1]) &&
					  isdigit(response[2]) &&
					  response[3]==':');
			m_logger->error("%s service registration: %s\n", 
					httpError?"HTTP error during":"Failed to parse result of", 
					response.c_str());
			return false;
		}
		if (doc.HasMember("id"))
		{
			m_uuid = new string(doc["id"].GetString());
			m_logger->info("Registered service '%s' with UUID %s.\n",
					service.getName().c_str(),
					m_uuid->c_str());
			if (doc.HasMember("bearer_token")){
				m_bearer_token = string(doc["bearer_token"].GetString());
				m_logger->debug("Bearer token issued for service '%s': %s",
						service.getName().c_str(),
						m_bearer_token.c_str());
			}

			return true;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to register service: %s.",
				doc["message"].GetString());
		}
		else
		{
			m_logger->error("Unexpected result from service registration %s",
					response.c_str());
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Register service failed %s.", e.what());
		return false;
	}
	return false;
}

/**
 * Unregister this service with the Fledge core
 *
 * @return bool	True if the service successfully unregistered
 */
bool ManagementClient::unregisterService()
{

	if (!m_uuid)
	{
		return false;	// Not registered
	}
	try {
		string url = "/fledge/service/";
		url += urlEncode(*m_uuid);
		auto res = this->getHttpClient()->request("DELETE", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s service unregistration: %s\n", 
								httpError?"HTTP error during":"Failed to parse result of", 
								response.c_str());
			return false;
		}
		if (doc.HasMember("id"))
		{
			delete m_uuid;
			m_uuid = new string(doc["id"].GetString());
			m_logger->info("Unregistered service %s.\n", m_uuid->c_str());
			return true;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to unregister service: %s.",
				doc["message"].GetString());
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Unregister service failed %s.", e.what());
		return false;
	}
	return false;
}

/**
 * Get the specified service. Supplied with a service
 * record that must either have the name or the type fields populated.
 * The call will populate the other fields of the service record.
 *
 * Note, if multiple service records match then only the first will be
 * returned.
 *
 * @param service	A partially filled service record that will be completed
 * @return bool		Return true if the service record was found
 */
bool ManagementClient::getService(ServiceRecord& service)
{
string payload;

	try {
		string url = "/fledge/service";
		if (!service.getName().empty())
		{
			url += "?name=" + urlEncode(service.getName());
		}
		else if (!service.getType().empty())
		{
			url += "?type=" + urlEncode(service.getType());
		}
		auto res = this->getHttpClient()->request("GET", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s fetching service record: %s\n", 
								httpError?"HTTP error while":"Failed to parse result of", 
								response.c_str());
			return false;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to register service: %s.",
				doc["message"].GetString());
			return false;
		}
		else
		{
			Value& serviceRecord = doc["services"][0];
			service.setAddress(serviceRecord["address"].GetString());
			service.setPort(serviceRecord["service_port"].GetInt());
			service.setProtocol(serviceRecord["protocol"].GetString());
			service.setManagementPort(serviceRecord["management_port"].GetInt());
			return true;
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Get service failed %s.", e.what());
		return false;
	}
	return false;
}

/**
 * Return all services registered with the Fledge core
 *
 * @param services	A vector of service records that will be populated
 * @return bool		True if the vecgtor was populated
 */
bool ManagementClient::getServices(vector<ServiceRecord *>& services)
{
string payload;

	try {
		string url = "/fledge/service";
		auto res = this->getHttpClient()->request("GET", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s fetching service record: %s\n", 
								httpError?"HTTP error while":"Failed to parse result of", 
								response.c_str());
			return false;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to register service: %s.",
				doc["message"].GetString());
			return false;
		}
		else
		{
			Value& records = doc["services"];
			for (auto& serviceRecord : records.GetArray())
			{
				ServiceRecord *service = new ServiceRecord(serviceRecord["name"].GetString(),
						serviceRecord["type"].GetString());
				service->setAddress(serviceRecord["address"].GetString());
				service->setPort(serviceRecord["service_port"].GetInt());
				service->setProtocol(serviceRecord["protocol"].GetString());
				service->setManagementPort(serviceRecord["management_port"].GetInt());
				services.push_back(service);
			}
			return true;
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Get services failed %s.", e.what());
		return false;
	}
	return false;
}

/**
 * Return all services registered with the Fledge core of a specified type
 *
 * @param services	A vector of service records that will be populated
 * @param type		The type of services to return
 * @return bool		True if the vecgtor was populated
 */
bool ManagementClient::getServices(vector<ServiceRecord *>& services, const string& type)
{
string payload;

	try {
		string url = "/fledge/service?type=";
		url += type;
		auto res = this->getHttpClient()->request("GET", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s fetching service record: %s\n", 
								httpError?"HTTP error while":"Failed to parse result of", 
								response.c_str());
			return false;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to register service: %s.",
				doc["message"].GetString());
			return false;
		}
		else
		{
			Value& records = doc["services"];
			for (auto& serviceRecord : records.GetArray())
			{
				ServiceRecord *service = new ServiceRecord(serviceRecord["name"].GetString(),
						serviceRecord["type"].GetString());
				service->setAddress(serviceRecord["address"].GetString());
				service->setPort(serviceRecord["service_port"].GetInt());
				service->setProtocol(serviceRecord["protocol"].GetString());
				service->setManagementPort(serviceRecord["management_port"].GetInt());
				services.push_back(service);
			}
			return true;
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Get services failed %s.", e.what());
		return false;
	}
	return false;
}

/**
 * Register interest in a configuration category. The service will be called 
 * with the updated confioguration category wheneven an item in the category
 * is added, removed or changed.
 *
 * @param category	The name of the category to register
 * @return bool		True if the registration was succesful
 */
bool ManagementClient::registerCategory(const string& category)
{
ostringstream convert;

	if (m_uuid == 0)
	{
		// Not registered with core
		m_logger->error("Service is not registered with the core - not registering configuration interest");
		return true;
	}
	try {
		convert << "{ \"category\" : \"" << JSONescape(category) << "\", ";
		convert << "\"service\" : \"" << *m_uuid << "\" }";
		auto res = this->getHttpClient()->request("POST", "/fledge/interest", convert.str());
		Document doc;
		string content = res->content.string();
		doc.Parse(content.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(content[0]) && isdigit(content[1]) && isdigit(content[2]) && content[3]==':');
			m_logger->error("%s category registration: %s\n", 
								httpError?"HTTP error during":"Failed to parse result of", 
								content.c_str());
			return false;
		}
		if (doc.HasMember("id"))
		{
			const char *reg_id = doc["id"].GetString();
			m_categories[category] = string(reg_id);
			m_logger->info("Registered configuration category %s, registration id %s.",
					category.c_str(), reg_id);
			return true;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to register configuration category: %s.",
				doc["message"].GetString());
		}
		else
		{
			m_logger->error("Failed to register configuration category: %s.",
					content.c_str());
		}
	} catch (const SimpleWeb::system_error &e) {
                m_logger->error("Register configuration category failed %s.", e.what());
                return false;
        }
        return false;
}

/**
 * Unregister interest in a configuration category. The service will no
 * longer be called when the configuration category is changed.
 *
 * @param category	The name of the configuration category to unregister
 * @return bool		True if the configuration category is unregistered
 */             
bool ManagementClient::unregisterCategory(const string& category)
{               
ostringstream convert;
        
        try {   
		string url = "/fledge/interest/";
		url += urlEncode(m_categories[category]);
        auto res = this->getHttpClient()->request("DELETE", url.c_str());
        } catch (const SimpleWeb::system_error &e) {
                m_logger->error("Unregister configuration category failed %s.", e.what());
                return false;
        }
        return false;
}

/**
 * Get the set of all configuration categories from the core micro service.
 *
 * @return ConfigCategories	The set of all confguration categories
 */
ConfigCategories ManagementClient::getCategories()
{
	try {
		string url = "/fledge/service/category";
		auto res = this->getHttpClient()->request("GET", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s fetching configuration categories: %s\n", 
								httpError?"HTTP error while":"Failed to parse result of", 
								response.c_str());
			throw new exception();
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to fetch configuration categories: %s.",
				doc["message"].GetString());
			throw new exception();
		}
		else
		{
			return ConfigCategories(response);
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Get config categories failed %s.", e.what());
		throw;
	}
}

/**
 * Return the content of the named category by calling the
 * management API of the Fledge core.
 *
 * @param  categoryName		The name of the categpry to return
 * @return ConfigCategory	The configuration category
 * @throw  exception		If the category does not exist or
 *				the result can not be parsed
 */
ConfigCategory ManagementClient::getCategory(const string& categoryName)
{
	try {
		string url = "/fledge/service/category/" + urlEncode(categoryName);
		auto res = this->getHttpClient()->request("GET", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s fetching configuration category for %s: %s\n", 
								httpError?"HTTP error while":"Failed to parse result of", 
								categoryName.c_str(), response.c_str());
			throw new exception();
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to fetch configuration category: %s.",
				doc["message"].GetString());
			throw new exception();
		}
		else
		{
			return ConfigCategory(categoryName, response);
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Get config category failed %s.", e.what());
		throw;
	}
}

/**
 * Set a category configuration item value
 *
 * @param categoryName  The given category name
 * @param itemName      The given item name
 * @param itemValue     The item value to set
 * @return              JSON string of the updated
 *                      category item
 * @throw               std::exception
 */
string ManagementClient::setCategoryItemValue(const string& categoryName,
					      const string& itemName,
					      const string& itemValue)
{
	try {
		string url = "/fledge/service/category/" + urlEncode(categoryName) + "/" + urlEncode(itemName);
		string payload = "{ \"value\" : \"" + itemValue + "\" }";
		auto res = this->getHttpClient()->request("PUT", url.c_str(), payload);
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s setting configuration category item value: %s\n", 
								httpError?"HTTP error while":"Failed to parse result of", 
								response.c_str());
			throw new exception();
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to set configuration category item value: %s.",
					doc["message"].GetString());
			throw new exception();
		}
		else
		{
			return response;
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Get config category failed %s.", e.what());
		throw;
	}
}

/**
 * Return child categories of a given category
 *
 * @param categoryName		The given category name
 * @return			JSON string with current child categories
 * @throw			std::exception
 */
ConfigCategories ManagementClient::getChildCategories(const string& categoryName)
{
	try
	{
		string url = "/fledge/service/category/" + urlEncode(categoryName) + "/children";
		auto res = this->getHttpClient()->request("GET", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) &&
					  isdigit(response[1]) &&
					  isdigit(response[2]) &&
					  response[3]==':');
			m_logger->error("%s fetching child categories of %s: %s\n",
					httpError?"HTTP error while":"Failed to parse result of",
					categoryName.c_str(),
					response.c_str());
			throw new exception();
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to fetch child categories of %s: %s.",
					categoryName.c_str(),
					doc["message"].GetString());

			throw new exception();
		}
		else
		{
			return ConfigCategories(response);
		}
	}
	catch (const SimpleWeb::system_error &e)
	{
		m_logger->error("Get child categories of %s failed %s.",
				categoryName.c_str(),
				e.what());
		throw;
	}
}

/**
 * Add child categories to a (parent) category
 *
 * @param parentCategory	The given category name
 * @param children		Categories to add under parent
 * @return			JSON string with current child categories
 * @throw			std::exception
 */
string ManagementClient::addChildCategories(const string& parentCategory,
					    const vector<string>& children)
{
	try {
		string url = "/fledge/service/category/" + urlEncode(parentCategory) + "/children";
		string payload = "{ \"children\" : [";

		for (auto it = children.begin(); it != children.end(); ++it)
		{
			payload += "\"" + JSONescape((*it)) + "\"";
			if ((it + 1) != children.end())
			{
				 payload += ", ";
			}
		}
		payload += "] }";
		auto res = this->getHttpClient()->request("POST", url.c_str(), payload);
		string response = res->content.string();
		Document doc;
		doc.Parse(response.c_str());
		if (doc.HasParseError() || !doc.HasMember("children"))
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s adding child categories: %s\n", 
								httpError?"HTTP error while":"Failed to parse result of", 
								response.c_str());
			throw new exception();
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to add child categories: %s.",
					doc["message"].GetString());
			throw new exception();
		}
		else
		{
			return response;
		}
	}
	catch (const SimpleWeb::system_error &e) {
		m_logger->error("Add child categories failed %s.", e.what());
		throw;
	}
}

/**
 * Get the asset tracking tuples
 * for a service or all services
 *
 * @param    serviceName	The serviceName to restrict data fetch
 *				If empty records for all services are fetched
 * @return		A vector of pointers to AssetTrackingTuple objects allocated on heap
 */
std::vector<AssetTrackingTuple*>& ManagementClient::getAssetTrackingTuples(const std::string serviceName)
{
	std::vector<AssetTrackingTuple*> *vec = new std::vector<AssetTrackingTuple*>();
	
	try {
		string url = "/fledge/track";
		if (serviceName != "")
		{
			url += "?service="+urlEncode(serviceName);
		}
		auto res = this->getHttpClient()->request("GET", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s fetch asset tracking tuples: %s\n", 
								httpError?"HTTP error during":"Failed to parse result of", 
								response.c_str());
			throw new exception();
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to fetch asset tracking tuples: %s.",
				doc["message"].GetString());
			throw new exception();
		}
		else
		{
			const rapidjson::Value& trackArray = doc["track"];
			if (trackArray.IsArray())
			{
				// Process every row and create the AssetTrackingTuple object
				for (auto& rec : trackArray.GetArray())
				{
					if (!rec.IsObject())
					{
						throw runtime_error("Expected asset tracker tuple to be an object");
					}
					AssetTrackingTuple *tuple = new AssetTrackingTuple(rec["service"].GetString(), rec["plugin"].GetString(), rec["asset"].GetString(), rec["event"].GetString());
					vec->push_back(tuple);
				}
			}
			else
			{
				throw runtime_error("Expected array of rows in asset track tuples array");
			}

			return (*vec);
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Fetch/parse of asset tracking tuples failed: %s.", e.what());
		//throw;
	}
	catch (...) {
		m_logger->error("Some other exception");
	}
}

/**
 * Add a new asset tracking tuple
 *
 * @param service	Service name
 * @param plugin	Plugin name
 * @param asset		Asset name
 * @param event		Event type
 * @return		whether operation was successful
 */
bool ManagementClient::addAssetTrackingTuple(const std::string& service, 
					const std::string& plugin, const std::string& asset, const std::string& event)
{
	ostringstream convert;

	try {
		convert << "{ \"service\" : \"" << JSONescape(service) << "\", ";
		convert << " \"plugin\" : \"" << plugin << "\", ";
		convert << " \"asset\" : \"" << asset << "\", ";
		convert << " \"event\" : \"" << event << "\" }";

		auto res = this->getHttpClient()->request("POST", "/fledge/track", convert.str());
		Document doc;
		string content = res->content.string();
		doc.Parse(content.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(content[0]) && isdigit(content[1]) && isdigit(content[2]) && content[3]==':');
			m_logger->error("%s asset tracking tuple addition: %s\n", 
								httpError?"HTTP error during":"Failed to parse result of", 
								content.c_str());
			return false;
		}
		if (doc.HasMember("fledge"))
		{
			const char *reg_id = doc["fledge"].GetString();
			return true;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to add asset tracking tuple: %s.",
				doc["message"].GetString());
		}
		else
		{
			m_logger->error("Failed to add asset tracking tuple: %s.",
					content.c_str());
		}
	} catch (const SimpleWeb::system_error &e) {
				m_logger->error("Failed to add asset tracking tuple: %s.", e.what());
				return false;
		}
		return false;
}

/**
 * Add an Audit Entry. Called when an auditable event occurs
 * to regsiter that event.
 *
 * Fledge API call example :
 *
 *  curl -X POST -d '{"source":"LMTR", "severity":"WARNING",
 *		      "details":{"message":"Engine oil pressure low"}}'
 *  http://localhost:8081/fledge/audit
 *
 * @param   code	The log code for the entry 
 * @param   severity	The severity level
 * @param   message	The JSON message to log
 */
bool ManagementClient::addAuditEntry(const std::string& code,
				     const std::string& severity,
				     const std::string& message)
{
	ostringstream convert;

	try {
		convert << "{ \"source\" : \"" << code << "\", ";
		convert << " \"severity\" : \"" << severity << "\", ";
		convert << " \"details\" : " << message << " }";

		auto res = this->getHttpClient()->request("POST",
							  "/fledge/audit",
							  convert.str());
		Document doc;
		string content = res->content.string();
		doc.Parse(content.c_str());

		if (doc.HasParseError())
		{
			bool httpError = (isdigit(content[0]) &&
					  isdigit(content[1]) &&
					  isdigit(content[2]) &&
					  content[3]==':');
			m_logger->error("%s audit entry: %s\n", 
					(httpError ?
					 "HTTP error during" :
					 "Failed to parse result of"), 
					content.c_str());
			return false;
		}

		bool ret = false;

		// Check server reply
		if (doc.HasMember("source"))
		{
			// OK
			ret = true;
		}
		else if (doc.HasMember("message"))
		{
			// Erropr
			m_logger->error("Failed to add audit entry: %s.",
				doc["message"].GetString());
		}
		else
		{
			// Erropr
			m_logger->error("Failed to add audit entry: %s.",
					content.c_str());
		}

		return ret;
	}
	catch (const SimpleWeb::system_error &e)
	{
		m_logger->error("Failed to add audit entry: %s.", e.what());
		return false;
	}
	return false;
}

/**
 * Checks and validate the JWT bearer token coming from HTTP request
 *
 * @param request	HTTP request object
 * @param claims	Map to fill with JWT public token claims
 * @return		True on success, false otherwise
 */
bool ManagementClient::verifyAccessBearerToken(shared_ptr<HttpServer::Request> request,
						map<string, string>& claims)
{
	string bearerToken = getAccessBearerToken(request);
	if (bearerToken.length() == 0)
	{
		m_logger->info("Access bearer token has empty value");
		return false;
	}
	return verifyBearerToken(bearerToken, claims);
}

/**
 * Checks and validate the JWT bearer token string
 *
 * @param bearerToken	The bearer token string
 * @param claims	Map to fill with JWT public token claims
 * @return		True on success, false otherwise
 */
bool ManagementClient::verifyBearerToken(const string& bearer_token,
					map<string, string>& claims)
{
	if (bearer_token.length() == 0)
	{
		m_logger->info("Bearer token has empty value");
		return false;
	}

	bool ret = true;

	// Check token already exists in cache:
	std::map<std::string, std::string>::iterator item;
	// Acquire lock
	m_mtx_rTokens.lock();

	item = m_received_tokens.find(bearer_token);
	if (item  == m_received_tokens.end())
	{
		bool verified = false;
		// Token does not exist:
		// Verify it by calling Fledge management endpoint
		string url = "/fledge/service/verify_token";
                string payload;
                SimpleWeb::CaseInsensitiveMultimap header;
                header.emplace("Authorization", "Bearer " + bearer_token);
                auto res = this->getHttpClient()->request("POST", url.c_str(), payload, header);
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) &&
					  isdigit(response[1]) &&
					  isdigit(response[2]) &&
					  response[3]==':');
			m_logger->error("%s error in service token verification: %s\n", 
					httpError?"HTTP error during":"Failed to parse result of", 
					response.c_str());
			verified = false;
		}
		else
		{
			if (doc.HasMember("error"))
			{
				if (doc["error"].IsString())
				{
					string error = doc["error"].GetString();
					m_logger->error("Failed to parse token verification result, error %s",
							error.c_str());
				}
				else
				{
					m_logger->error("Failed to parse token verification result");
				}
				verified = false;
			}
			else
			{
				verified = true;

				// Set token claims in the input map
				if (doc["aud"].IsString() &&
				    doc["sub"].IsString() &&
				    doc["iss"].IsString() &&
				    doc["exp"].IsUint())
				{
					claims["aud"] = doc["aud"].GetString();
					claims["sub"] = doc["sub"].GetString();
					claims["iss"] = doc["iss"].GetString();
					claims["exp"] = std::to_string(doc["exp"].GetUint());
				}
				else
				{
					 m_logger->error("Token claims do not contain string values");
				}
			}
		}

		if (verified)
		{
			// Token verified, store the token
			m_received_tokens[bearer_token] = "added";
		}
		else
		{
			ret = false;
			m_logger->error("Micro service bearer token '%s' not verified.",
					bearer_token.c_str());
		}
	}
	else
	{
		// A validated token exists: check expiration time
		vector<string> elems = JWTTokenSplit(bearer_token, '.');
		// Add missing base64 padding
		if (elems[1].length() % 4 != 0)
		{
			elems[1] += "=";
		}
		if (elems[1].length() % 4 != 0)
		{
			elems[1] += "=";
		}
		// Base64 decode of second part of bearer token (with public claims)
		string plainData = Crypto::Base64::decode(elems[1]);
		Document doc;
		doc.Parse(plainData.c_str());

		// JSON parsing check of token claims
		if (doc.HasParseError())
		{
			m_logger->error("Failure while parsing JSON claims of bearer token, "
					"error %s, input data %s",
					GetParseError_En(doc.GetParseError()),
					plainData.c_str());
			return false;
		}

		unsigned long expiration;
		if (doc["exp"].IsUint())
		{
			expiration = doc["exp"].GetUint();
		}
		else
		{
			m_logger->error("Failure while parsing 'exp' token claim of bearer token, "
					"error %s, input data %s",
					"not a number",
					plainData.c_str());
			return false;
		}
		unsigned long now = time(NULL);

		// Check expiration
		if (now >= expiration)
		{
			ret = false;
			// Remove token from received ones
			m_received_tokens.erase(bearer_token);

			m_logger->error("Micro service bearer token '%s' has expired.",
					bearer_token.c_str());
		}
		else
		{
			// Token still valid, set token claims in the input map
			claims["aud"] = doc["aud"].GetString();
			claims["sub"] = doc["sub"].GetString();
			claims["iss"] = doc["iss"].GetString();
			claims["exp"] = std::to_string(doc["exp"].GetUint());
		}
	}

	// Release lock
	m_mtx_rTokens.unlock();

	m_logger->error("Token verified %d, claims %s:%s:%s:%s",
			ret,
			claims["aud"].c_str(),
			claims["sub"].c_str(),
			claims["iss"].c_str(),
			claims["exp"].c_str());

	return ret;
}

/**
 * Refresh the JWT bearer token coming from HTTP request
 *
 * @param request       HTTP request object
 * @param claims        Map to fill with JWT public token claims
 * @return              New bearer token on success, empty string otherwise
 */
string ManagementClient::refreshAccessBearerToken(shared_ptr<HttpServer::Request> request)
{
	string bearer_token = getAccessBearerToken(request);
	if (bearer_token.length() == 0)
	{
		return "";
	}

	return refreshBearerToken(bearer_token);
}

/**
 * Refresh the JWT bearer token string
 *
 * @param request       HTTP request object
 * @param claims        Map to fill with JWT public token claims
 * @return              New bearer token on success, empty string otherwise
 */
string ManagementClient::refreshBearerToken(const string& bearer_token)
{
	if (bearer_token.length() == 0)
	{
		return "";
	}

	bool ret = false;

	// Check token already exists in cache:
	std::map<std::string, std::string>::iterator item;
	m_mtx_rTokens.lock();

	// Refresh it by calling Fledge management endpoint
	string newToken;
	string url = "/fledge/service/refresh_token";
	string payload;
	SimpleWeb::CaseInsensitiveMultimap header;
	header.emplace("Authorization", "Bearer " + bearer_token);
	auto res = this->getHttpClient()->request("POST", url.c_str(), payload, header);
	Document doc;
	string response = res->content.string();
	doc.Parse(response.c_str());
	if (doc.HasParseError())
	{
		bool httpError = (isdigit(response[0]) &&
				isdigit(response[1]) &&
				isdigit(response[2]) &&
				response[3]==':');
		m_logger->error("%s error in service token refresh: %s\n",
				httpError?"HTTP error during":"Failed to parse result of",
				response.c_str());
		ret = false;
	}
	else
	{
		if (doc.HasMember("error"))
		{
			if (doc["error"].IsString())
			{
				string error = doc["error"].GetString();
				m_logger->error("Failed to parse token refresh result, error %s",
						error.c_str());
			}
			else
			{
				m_logger->error("Failed to parse token refresh result");
			}
			ret = false;
		}
		else if (doc.HasMember("bearer_token"))
		{
			// Set new token
			newToken = doc["bearer_token"].GetString();
			ret = true;
		}
		else
		{
			m_logger->error("Bearer token not found in token refresh result");
			ret = false;
		}
	}

	if (ret)
	{
		// Remove old token from received ones
		m_received_tokens.erase(bearer_token);
	}

	m_mtx_rTokens.unlock();

	return newToken;
}

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
#ifdef DEBUG_BEARER_TOKEN
				m_logger->debug("Bearer token issued for service '%s': %s",
						service.getName().c_str(),
						m_bearer_token.c_str());
#endif
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
 * Restart this service by sendign a request to the Fledge core
 *
 * @return bool	True if the service successfully requested restart
 */
bool ManagementClient::restartService()
{

	if (!m_uuid)
	{
		return false;	// Not registered
	}
	try {
		string url = "/fledge/service/";
		url += urlEncode(*m_uuid);
		url += "/restart";
		auto res = this->getHttpClient()->request("PUT", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s service restart: %s\n", 
								httpError?"HTTP error during":"Failed to parse result of", 
								response.c_str());
			return false;
		}
		if (doc.HasMember("id"))
		{
			delete m_uuid;
			m_uuid = new string(doc["id"].GetString());
			m_logger->info("Restart service %s.\n", m_uuid->c_str());
			return true;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to restart service: %s.",
				doc["message"].GetString());
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Restart service failed %s.", e.what());
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
 * with the updated configuration category whenever an item in the category
 * is added, removed or changed.
 *
 * @param category	The name of the category to register
 * @return bool		True if the registration was succesful
 */
bool ManagementClient::registerCategoryChild(const string& category)
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
		convert << "\"child\" : \"" << "True" << "\", ";
		convert << "\"service\" : \"" << *m_uuid << "\" }";

		auto res = this->getHttpClient()->request("POST", "/fledge/interest", convert.str());
		Document doc;
		string content = res->content.string();
		doc.Parse(content.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(content[0]) && isdigit(content[1]) && isdigit(content[2]) && content[3]==':');
			m_logger->error("%s child category registration: %s\n",
								httpError?"HTTP error during":"Failed to parse result of",
								content.c_str());
			return false;
		}
		if (doc.HasMember("id"))
		{
			const char *reg_id = doc["id"].GetString();
			m_categories[category] = string(reg_id);
			m_logger->info("Registered child configuration category %s, registration id %s.",
					category.c_str(), reg_id);
			return true;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to register child configuration category: %s.",
				doc["message"].GetString());
		}
		else
		{
			m_logger->error("Failed to register child configuration category: %s.",
					content.c_str());
		}
	} catch (const SimpleWeb::system_error &e) {
                m_logger->error("Register child configuration category failed %s.", e.what());
                return false;
        }
        return false;
}


/**
 * Register interest in a configuration category
 *
 * @param category	The name of the configuration category to register
 * @return bool		True if the configuration category has been registered
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
		string response = res->content.string();
		if (res->status_code.compare("200 OK") == 0)
		{
			return ConfigCategory(categoryName, response);
		}
		Document doc;
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s fetching configuration category for %s: %s\n", 
								httpError?"HTTP error while":"Failed to parse result of", 
								categoryName.c_str(), response.c_str());
			throw new exception();
		}
		else if (doc.HasMember("message") && doc["message"].IsString())
		{
			m_logger->error("Failed to fetch configuration category: %s.",
				doc["message"].GetString());
			throw new exception();
		}
		else
		{
			m_logger->error("Failed to fetch configuration category: %s.",
				response.c_str());
			throw new exception();
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
		if (res->status_code.compare("200 OK") == 0)
		{
			return response;
		}
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
			m_logger->error("Failed to set configuration category item value: %s.",
					response.c_str());
			throw new exception();
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

					// Do not load "store" events as they bill be loaded by getStorageAssetTrackingTuples()
					if (rec["event"].GetString() == "store")
					{
						continue;
					}

					// Note: deprecatedTimestamp NULL value is returned as ""
					// otherwise it's a string DATE
					bool deprecated = rec.HasMember("deprecatedTimestamp") &&
					    strlen(rec["deprecatedTimestamp"].GetString());

					AssetTrackingTuple *tuple = new AssetTrackingTuple(rec["service"].GetString(),
									rec["plugin"].GetString(),
									rec["asset"].GetString(),
									rec["event"].GetString(),
									deprecated);

					m_logger->debug("Adding AssetTracker tuple for service %s: %s:%s:%s, " \
							"deprecated state is %d",
							rec["service"].GetString(),
							rec["plugin"].GetString(),
							rec["asset"].GetString(),
							rec["event"].GetString(),
							deprecated);
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
		m_logger->error("Fetch/parse of asset tracking tuples for service %s failed: %s.", serviceName.c_str(), e.what());
		//throw;
	}
	catch (...) {
		m_logger->error("Unexpected exception when retrieving asset tuples for service %s:, serviceName.c_str()");
	}
	return *vec;
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
					const std::string& plugin,
					const std::string& asset,
					const std::string& event)
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
 * Checks and validate the JWT bearer token object as reference
 *
 * @param request	The bearer token object
 * @return		True on success, false otherwise
 */
bool ManagementClient::verifyAccessBearerToken(BearerToken& token)
{
	if (!token.exists())
	{
		m_logger->warn("Access bearer token has empty value");
		return false;
	}
	return verifyBearerToken(token);
}

/**
 * Checks and validate the JWT bearer token coming from HTTP request
 *
 * @param request	HTTP request object
 * @return		True on success, false otherwise
 */
bool ManagementClient::verifyAccessBearerToken(shared_ptr<HttpServer::Request> request)
{
	BearerToken bT(request);
	return this->verifyBearerToken(bT);
}

/**
 * Refresh the JWT bearer token string
 *
 * @param currentToken	Current bearer token
 * @param newToken	New issued bearer token being set
 * @return              True on success, false otherwise
 */
bool ManagementClient::refreshBearerToken(const string& currentToken,
					string& newToken)
{
	if (currentToken.length() == 0)
	{
		newToken.clear();
		return false;
	}

	bool ret = false;

	// Refresh it by calling Fledge management endpoint
	string url = "/fledge/service/refresh_token";
	string payload;
	SimpleWeb::CaseInsensitiveMultimap header;
	header.emplace("Authorization", "Bearer " + currentToken);
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
				m_logger->error("Failed to refresh refresh bearer token, error %s",
						error.c_str());
			}
			else
			{
				m_logger->error("Failed to refresh beearer token result: %s",
						response.c_str());
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
			m_logger->error("Bearer token not found in token refresh result: %s",
					response.c_str());
			ret = false;
		}
	}

	m_mtx_rTokens.lock();
	if (ret)
	{
		// Remove old token from received ones
		m_received_tokens.erase(currentToken);
	}
	else
	{
		newToken.clear();
	}

	m_mtx_rTokens.unlock();

	return ret;
}

/**
 * Checks and validate the JWT bearer token string
 *
 * Input token internal data will be set
 * with new values or cached ones
 *
 * @param bearerToken	The bearer token object
 * @return		True on success, false otherwise
 */
bool ManagementClient::verifyBearerToken(BearerToken& bearerToken)
{
	if (!bearerToken.exists())
	{
		m_logger->warn("Bearer token has empty value");
		return false;
	}

	bool ret = true;
	const string& token = bearerToken.token();

	// Check token already exists in cache:
	map<string, BearerToken>::iterator item;
	// Acquire lock
	m_mtx_rTokens.lock();

	item = m_received_tokens.find(token);
	if (item  == m_received_tokens.end())
	{
		// Token is not in the cache
		bool verified = false;
		// Token does not exist:
		// Verify it by calling Fledge management endpoint
		string url = "/fledge/service/verify_token";
                string payload;
                SimpleWeb::CaseInsensitiveMultimap header;
                header.emplace("Authorization", "Bearer " + token);
                auto res = this->getHttpClient()->request("POST", url.c_str(), payload, header);
		string response = res->content.string();

		// Parse JSON message and store claims in input token object
		verified = bearerToken.verify(response);
		if (verified)
		{
			// Token verified, store the token object
			m_received_tokens.emplace(token, bearerToken);
		}
		else
		{
			ret = false;
			m_logger->error("Micro service bearer token '%s' not verified.",
					token.c_str());
		}
#ifdef DEBUG_BEARER_TOKEN
		m_logger->debug("New token verified by core API endpoint %d, claims %s:%s:%s:%ld",
				ret,
				bearerToken.getAudience().c_str(),
				bearerToken.getSubject().c_str(),
				bearerToken.getIssuer().c_str(),
				bearerToken.getExpiration());
#endif
	}
	else
	{
		// Token is in the cache
		unsigned long expiration = (*item).second.getExpiration();
		unsigned long now = time(NULL);

		// Check expiration
		if (now >= expiration)
		{
			ret = false;
			// Remove token from received ones
			m_received_tokens.erase(token);

			m_logger->error("Micro service bearer token expired.");
		}

		// Set input token object as per cached data
		bearerToken = (*item).second;

#ifdef DEBUG_BEARER_TOKEN
		m_logger->debug("Existing token already verified %d, claims %s:%s:%s:%ld",
				ret,
				(*item).second.getAudience().c_str(),
				(*item).second.getSubject().c_str(),
				(*item).second.getIssuer().c_str(),
				(*item).second.getExpiration());
#endif
	}

	// Release lock
	m_mtx_rTokens.unlock();

	return ret;
}

/**
 * Request that the core proxy a URL to the service. URL's in the public Fledge API will be forwarded
 * to the service API of the named service.
 *
 * @param serviceName	The name of the service to send the request to
 * @param operation	The type of operations; post, put, get or delete
 * @param publicEndpoint	The URL inthe Fledge public API to be proxied
 * @param privateEnpoint	The URL in the service API of the named service to which the reuests will be proxied.
 * @return	bool		True if the proxy request was accepted
 */
bool ManagementClient::addProxy(const std::string& serviceName,
		const std::string& operation,
		const std::string& publicEndpoint,
		const std::string& privateEndpoint)
{
	ostringstream convert;

	try {
		convert << "{ \"" << operation << "\" : { ";
		convert << "\"" << publicEndpoint << "\" : ";
		convert << "\"" << privateEndpoint << "\" } ";
		convert << "\"service_name\" : \"" << serviceName << "\" }";

		auto res = this->getHttpClient()->request("POST",
							  "/fledge/proxy",
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
			m_logger->error("%s proxy addition: %s\n", 
					(httpError ?
					 "HTTP error during" :
					 "Failed to parse result of"), 
					content.c_str());
			return false;
		}


		bool result = false;
                if (res->status_code[0] == '2') // A 2xx response
		{
			result = true;
		}

		if (doc.HasMember("message"))
		{
			m_logger->error("Add proxy entry: %s.",
				doc["message"].GetString());
			return result;
		}
		return result;
	}
	catch (const SimpleWeb::system_error &e)
	{
		m_logger->error("Failed to add proxt entry: %s.", e.what());
		return false;
	}
	return false;
}

/**
 * Request that the core proxy a URL to the service. URL's in the public Fledge API will be forwarded
 * to the service API of the named service.
 *
 * @param serviceName	The name of the service to send the request to
 * @param endpoints	The set of endpoints to be mapped
 * @return	bool		True if the proxy request was accepted
 */
bool ManagementClient::addProxy(const std::string& serviceName,
			const map<std::string, vector<pair<string, string> > >& endpoints)
{
	ostringstream convert;

	try {

		convert << "{ ";
		for (auto const& op : endpoints)
		{
			convert << "\"" << op.first << "\" : { ";
			bool first = true;
			for (auto const& ep : op.second)
			{
				if (!first)
					convert << ", ";
				first = false;
				convert << "\"" << ep.first << "\" :";
				convert << "\"" << ep.second << "\"";
			}
			convert << "}, ";
		}
		convert << "\"service_name\" : \"" << serviceName << "\" }";

		auto res = this->getHttpClient()->request("POST",
							  "/fledge/proxy",
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
			m_logger->error("%s proxy addition: %s\n", 
					(httpError ?
					 "HTTP error during" :
					 "Failed to parse result of"), 
					content.c_str());
			return false;
		}

		bool result = false;
                if (res->status_code[0] == '2') // A 2xx response
		{
			result = true;
		}

		if (doc.HasMember("message"))
		{
			m_logger->error("Add proxy entries: %s.",
				doc["message"].GetString());
			return result;
		}
		return result;
	}
	catch (const SimpleWeb::system_error &e)
	{
		m_logger->error("Failed to add proxy entry: %s.", e.what());
		return false;
	}
	return false;
}

/**
 * Delete the current proxy endpoitn for the named service. Normally called prior
 * to the service shutting down.
 *
 * @param serviceName	THe name of the service to sto the proxying for
 * @return bool	True if the request succeeded
 */
bool ManagementClient::deleteProxy(const std::string& serviceName)
{
	bool result = false;
	try {
		string url = "/fledge/proxy/";
		url += urlEncode(serviceName);
		auto res = this->getHttpClient()->request("DELETE", url.c_str());
                if (res->status_code[0] == '2') // A 2xx response
		{
			result = true;;
		}
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
			m_logger->error("%s service proxy deletion: %s\n", 
					httpError?"HTTP error during":"Failed to parse result of", 
						response.c_str());
			return result;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Stop proxy of endpoints for service: %s.",
				doc["message"].GetString());
			return result;
		}
		else
		{
			m_logger->info("API proxying has been stopped");
			return result;
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Proxy deletion failed %s.", e.what());
		return false;
	}
	return false;
}

/**
 * Get the asset tracking tuple
 * for a service and asset name
 *
 * @param    serviceName	The serviceName to restrict data fetch
 * @param    assetName		The asset name that belongs to the service
 * @param    event		The associated event type
 * @return		A vector of pointers to AssetTrackingTuple objects allocated on heap
 */
AssetTrackingTuple* ManagementClient::getAssetTrackingTuple(const std::string& serviceName,
							const std::string& assetName,
							const std::string& event)
{
	AssetTrackingTuple* tuple = NULL;
	try {
		string url = "/fledge/track";
		if (serviceName == "" && assetName == "" && event == "")
		{
			m_logger->error("Failed to fetch asset tracking tuple: " \
					"service name, asset name and event type are required.");
			throw new exception();
		}

		url += "?service=" + urlEncode(serviceName);
		url += "&asset=" + urlEncode(assetName) + "&event=" + event;

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
			m_logger->error("%s fetch asset tracking tuple: %s\n",
					httpError?"HTTP error during":"Failed to parse result of",
					response.c_str());
			throw new exception();
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to fetch asset tracking tuple: %s.",
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

					// Note: deprecatedTimestamp NULL value is returned as ""
					// otherwise it's a string DATE
					bool deprecated = rec.HasMember("deprecatedTimestamp") &&
					    strlen(rec["deprecatedTimestamp"].GetString());

					// Create a new AssetTrackingTuple object, to be freed by the caller
					tuple = new AssetTrackingTuple(rec["service"].GetString(),
									rec["plugin"].GetString(),
									rec["asset"].GetString(),
									rec["event"].GetString(),
									deprecated);

					m_logger->debug("Adding AssetTracker tuple for service %s: %s:%s:%s, " \
							"deprecated state is %d",
							rec["service"].GetString(),
							rec["plugin"].GetString(),
							rec["asset"].GetString(),
							rec["event"].GetString(),
							deprecated);
				}
			}
			else
			{
				throw runtime_error("Expected array of rows in asset track tuples array");
			}

			return tuple;
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Fetch/parse of asset tracking tuples for service %s failed: %s.",
				serviceName.c_str(),
				e.what());
	} catch (...) {
		m_logger->error("Unexpected exception when retrieving asset tuples for service %s",
				serviceName.c_str());
	}

	return tuple;
}

/**
 * Get the asset tracking tuples for all the deprecated assets
 *
 * @return		A vector of pointers to AssetTrackingTuple objects allocated on heap
 */
AssetTrackingTable* ManagementClient::getDeprecatedAssetTrackingTuples()
{
	AssetTrackingTable* table = NULL;
	try {
		string url = "/fledge/track?deprecated=true";

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
			m_logger->error("%s fetch asset tracking tuple: %s\n",
					httpError?"HTTP error during":"Failed to parse result of",
					response.c_str());
			throw new exception();
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to fetch asset tracking tuple: %s.",
				doc["message"].GetString());
			throw new exception();
		}
		else
		{
			const rapidjson::Value& trackArray = doc["track"];
			if (trackArray.IsArray())
			{
				table = new AssetTrackingTable();
				// Process every row and create the AssetTrackingTuple object
				for (auto& rec : trackArray.GetArray())
				{
					if (!rec.IsObject())
					{
						throw runtime_error("Expected asset tracker tuple to be an object");
					}

					// Note: deprecatedTimestamp NULL value is returned as ""
					// otherwise it's a string DATE
					bool deprecated = rec.HasMember("deprecatedTimestamp") &&
					    strlen(rec["deprecatedTimestamp"].GetString());

					// Create a new AssetTrackingTuple object, to be freed by the caller
					AssetTrackingTuple *tuple = new AssetTrackingTuple(rec["service"].GetString(),
									rec["plugin"].GetString(),
									rec["asset"].GetString(),
									rec["event"].GetString(),
									deprecated);

					m_logger->debug("Adding AssetTracker tuple for service %s: %s:%s:%s, " \
							"deprecated state is %d",
							rec["service"].GetString(),
							rec["plugin"].GetString(),
							rec["asset"].GetString(),
							rec["event"].GetString(),
							deprecated);

					table->add(tuple);
				}
			}
			else
			{
				throw runtime_error("Expected array of rows in asset track tuples array");
			}

			return table;
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Fetch/parse of deprecated asset tracking tuples failed: %s.",
				e.what());
	} catch (...) {
		m_logger->error("Unexpected exception when retrieving asset tuples for deprecated assets");
	}

	return table;
}

/**
 * Return the content of the named ACL by calling the
 * management API of the Fledge core.
 *
 * @param  aclName		The name of the ACL to return
 * @return ACL			The ACL class
 * @throw  exception		If the ACL does not exist or
 *				the JSON result can not be parsed
 */
ACL ManagementClient::getACL(const string& aclName)
{
	try {
		string url = "/fledge/ACL/" + urlEncode(aclName);

		auto res = this->getHttpClient()->request("GET", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) &&
					  isdigit(response[1]) &&
					  isdigit(response[2]) && response[3]==':');
			m_logger->error("%s fetching ACL for %s: %s\n",
					httpError?"HTTP error while":"Failed to parse result of",
					aclName.c_str(),
					response.c_str());
			throw new exception();
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to fetch ACL: %s.",
				doc["message"].GetString());
			throw new exception();
		}
		else
		{
			// Success
			return ACL(response);
		}
	} catch (const SimpleWeb::system_error &e) {
		m_logger->error("Get ACL failed %s.", e.what());
		throw;
	}
}

/**
 * Get the asset tracking tuple
 * for a service and asset name
 *
 * @param    serviceName        The serviceName to restrict data fetch
 * @param    assetName          The asset name that belongs to the service
 * @param    event              The associated event type
 * @param    dp			The datapoints Type
 * @param    c			The count of datapoints
 * @return              	A pointer to AssetTrackingTuple objects allocated on heap
 */
StorageAssetTrackingTuple* ManagementClient::getStorageAssetTrackingTuple(const std::string& serviceName,
                                                        const std::string& assetName,
                                                        const std::string& event,
							const std::string& dp,
							const unsigned int& c)
{
	
        StorageAssetTrackingTuple* tuple = NULL;
        try {
                string url = "/fledge/track";
                if (serviceName == "" || assetName == "" || event == "")
                {
                        m_logger->error("Failed to fetch storage asset tracking tuple: " \
                                        "service name, asset name and event type are required.");
                        throw new exception();
                }

                url += "?service=" + urlEncode(serviceName);
                url += "&asset=" + urlEncode(assetName) + "&event=" + event;

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
                        m_logger->error("%s fetch storage asset tracking tuple: %s\n",
                                        httpError?"HTTP error during":"Failed to parse result of",
                                        response.c_str());
                        throw new exception();
                }
                else if (doc.HasMember("message"))
                {
                        m_logger->error("Failed to fetch storage asset tracking tuple: %s.",
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
					 m_logger->debug("%s:%d Inside for loop of trackArray ", __FUNCTION__, __LINE__);

                                        if (!rec.IsObject())
                                        {
                                                throw runtime_error("Expected storage asset tracker tuple to be an object");
                                        }

                                        // Note: deprecatedTimestamp NULL value is returned as ""
                                        // otherwise it's a string DATE
                                        bool deprecated = rec.HasMember("deprecatedTimestamp") &&
                                            strlen(rec["deprecatedTimestamp"].GetString());

					std::string data ;
                                        if (!rec.HasMember("data"))
                                        {
                                                throw runtime_error("Expected storage asset tracker tuple to contain member data");
                                        }

                                        const rapidjson::Value& dataVal = rec["data"];
                                        if (!dataVal.IsObject())
                                        {
                                                throw runtime_error("Expected data in storage asset tracker tuple to be an object");
                                        }

                                        if (!dataVal.HasMember("datapoints"))
                                        {
                                                 throw runtime_error("Expected asset tracker tuple to contain datapoints");
                                        }

                                        if (dataVal.ObjectEmpty())
                                        {
                                                m_logger->error("%s:%d dataVal  Object empty " , __FUNCTION__, __LINE__);
                                                continue;
                                        }

                                        if (!dataVal["datapoints"].IsArray())
                                        {
                                                throw runtime_error("Expected datapoints to be object");
                                        }

					std::string datapoints;
					for (auto& r : dataVal["datapoints"].GetArray())
					{
						if (!r.IsString())
						{
							throw runtime_error("Expected r to be string");
						}
						else
						{
							datapoints.append(r.GetString());
							datapoints.append(",");
						}
					}


					if (datapoints[datapoints.size()-1] == ',')
					{
						datapoints.pop_back();
					}

					if(validateDatapoints(dp,datapoints))
					{
						//datapoints in db not same as in arg, continue
						m_logger->debug("%s:%d :Datapoints in db not same as in arg",
								__FUNCTION__,
								__LINE__);
						continue;
					}
					
                                        if (!dataVal.HasMember("count"))
                                        {
                                                 throw runtime_error("Expected asset tracker tuple to contain count");
                                        }

                                        if (!dataVal["count"].IsInt())
                                        {
                                                throw runtime_error("Expected count in data to be int");
                                        }
                                        int count = dataVal["count"].GetInt();
					if ( count != c)
					{
						// count not same, continue
						m_logger->debug("%s:%d :count in db not same as received in arg",
								__FUNCTION__,
								__LINE__);
						continue;
					}

                                        // Create a new AssetTrackingTuple object, to be freed by the caller
                                        tuple = new StorageAssetTrackingTuple(rec["service"].GetString(),
                                                                        rec["plugin"].GetString(),
                                                                        rec["asset"].GetString(),
                                                                        rec["event"].GetString(),
                                                                        deprecated,
									datapoints,
									count);

                                        m_logger->debug("%s:%d : Adding StorageAssetTracker tuple for service %s: %s:%s:%s, " \
                                                        "deprecated state is %d, datapoints %s , count %d",__FUNCTION__, __LINE__,
                                                        rec["service"].GetString(),
                                                        rec["plugin"].GetString(),
                                                        rec["asset"].GetString(),
                                                        rec["event"].GetString(),
                                                        deprecated, datapoints.c_str(), count);
 

                                }
                        }
                        else
                        {
                                throw runtime_error("Expected array of rows in storage asset track tuples array");
                        }

                        return tuple;
                }
        } catch (const SimpleWeb::system_error &e) {
                m_logger->error("Fetch/parse of storage asset tracking tuples for service %s failed: %s.",
                                serviceName.c_str(),
                                e.what());
        } catch (...) {
                m_logger->error("Unexpected exception when retrieving storage asset tuples for service %s",
                                serviceName.c_str());
        }

        return tuple;
}
	
/**
 * Add a new asset tracking tuple
 *
 * @param service	Service name
 * @param plugin	Plugin name
 * @param asset		Asset name
 * @param event		Event type
 * @param deprecated	Deprecated or not
 * @param datapoints	Datapoints type
 * @param count		Count Type
 * @return		whether operation was successful
 */
bool ManagementClient::addStorageAssetTrackingTuple(const std::string& service, 
					const std::string& plugin,
					const std::string& asset,
					const std::string& event,
					const bool& deprecated,
					const std::string& datapoints,
					const int& count)
{
	ostringstream convert;
	std::string d ;
        for ( int i = 0; i < datapoints.size(); ++i)
        {
                if (datapoints[i] == ',')
                {
                        d.append("\",\"");
                }
                else
                        d.append(1,datapoints[i]);
        }

	try {
		convert << "{ \"service\" : \"" << JSONescape(service) << "\", ";
		convert << " \"plugin\" : \"" << plugin << "\", ";
		convert << " \"asset\" : \"" << asset << "\", ";
		convert << " \"event\" : \"" << event << "\", ";
		convert << " \"deprecated\" :\"" << deprecated << "\", ";
		convert << " \"data\"  :  { \"datapoints\" : \[ \"" << d << "\" ], ";
		convert << " \"count\" : " << count << " } }";

		auto res = this->getHttpClient()->request("POST", "/fledge/track", convert.str());
		if (res->status_code[0] == '2') // A 2xx response
                {
                        return true;
                }

		Document doc;
		string content = res->content.string();
		doc.Parse(content.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(content[0]) && isdigit(content[1]) && isdigit(content[2]) && content[3]==':');
			m_logger->error("%s:%d , %s storage asset tracking tuple addition: %s\n",__FUNCTION__, __LINE__, 
								httpError?"HTTP error during":"Failed to parse result of", 
								content.c_str());
			return false;
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("%s:%d Failed to add storage asset tracking tuple: %s.",__FUNCTION__, __LINE__,
				doc["message"].GetString());
		}
		else
		{
			m_logger->error("%s:%d Failed to add storage asset tracking tuple: %s.",__FUNCTION__, __LINE__,
					content.c_str());
		}
	} catch (const SimpleWeb::system_error &e) {
				m_logger->error("%s:%d Failed to add storage asset tracking tuple: %s.",__FUNCTION__, __LINE__, e.what());
				return false;
		}
		return false;
}

/**
 * Get the storage asset tracking tuples
 * for a service or all services
 *
 * @param    serviceName        The serviceName to restrict data fetch
 *                              If empty records for all services are fetched
 * @return              	A vector of pointers to AssetTrackingTuple objects allocated on heap
 */
std::vector<StorageAssetTrackingTuple*>& ManagementClient::getStorageAssetTrackingTuples(const std::string serviceName)
{
        std::vector<StorageAssetTrackingTuple*> *vec = new std::vector<StorageAssetTrackingTuple*>();

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

                                        // Note: deprecatedTimestamp NULL value is returned as ""
                                        // otherwise it's a string DATE
                                        bool deprecated = rec.HasMember("deprecatedTimestamp") &&
                                            strlen(rec["deprecatedTimestamp"].GetString());

                                        std::string data ;
                                        if (!rec.HasMember("data"))
                                        {
                                                throw runtime_error("Expected asset tracker tuple to contain member data");
                                        }

                                        const rapidjson::Value& dataVal = rec["data"];
                                        if (!dataVal.IsObject())
                                        {
                                                throw runtime_error("Expected data asset tracker tuple to be an object");
                                        }

					if (dataVal.ObjectEmpty())
					{
						m_logger->debug("%s:%d dataVal Object empty " , __FUNCTION__, __LINE__);
						continue;
					}

                                        if (!dataVal.HasMember("datapoints"))
                                        {
                                                 throw runtime_error("Expected asset tracker tuple to contain datapoints");
                                        }

					if (!dataVal["datapoints"].IsArray())
                                        {
                                                throw runtime_error("Expected datapoints to be array");
                                        }

                                        std::string datapoints;
                                        for (auto& r : dataVal["datapoints"].GetArray())
                                        {
                                                if (!r.IsString())
                                                {
                                                        throw runtime_error("Expected individual datapoints in datapoints array to be string");
                                                }
                                                else
                                                {
                                                        datapoints.append(r.GetString());
                                                        datapoints.append(",");
                                                }
                                        }

					if( datapoints[datapoints.size()-1] == ',')
					{
						datapoints.pop_back();
					}

                                        if (!dataVal.HasMember("count"))
                                        {
                                                 throw runtime_error("Expected asset tracker tuple to contain count");
                                        }

                                        if (!dataVal["count"].IsInt())
                                        {
                                                throw runtime_error("Expected count in data to be int");
                                        }
                                        int count = dataVal["count"].GetInt();
                                        m_logger->debug("%s:%d count = %d  ", __FUNCTION__, __LINE__, count);

                                        StorageAssetTrackingTuple *tuple = new StorageAssetTrackingTuple(rec["service"].GetString(),
                                                                        rec["plugin"].GetString(),
                                                                        rec["asset"].GetString(),
                                                                        rec["event"].GetString(),
                                                                        deprecated, datapoints, count);

                                        m_logger->debug("%s:%d: Adding StorageAssetTracker tuple for service %s: %s:%s:%s, " \
                                                        "deprecated state is %d, datapoints %s , count %d" ,__FUNCTION__, __LINE__,
                                                        rec["service"].GetString(),
                                                        rec["plugin"].GetString(),
                                                        rec["asset"].GetString(),
                                                        rec["event"].GetString(),
                                                        deprecated, datapoints.c_str(), count);
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
                m_logger->error("Fetch/parse of asset tracking tuples for service %s failed: %s.", serviceName.c_str(), e.what());
        }
        catch (...) {
                m_logger->error("Unexpected exception when retrieving asset tuples for service %s", serviceName.c_str());
        }
        return *vec;
}

/**
 * Compare the datapoints to be equal or not, they can be '"' enclosed 
 *
 * @param    dp1        The datapoint to compare, enclosed in '"'
 * @param    dp2        The datapoint to compare
 * @return   int        integer depicting result of comparison, 0 on equal 
 */

int ManagementClient::validateDatapoints(std::string dp1, std::string dp2)
{
	std::string temp;
	for (int i = 0; i < dp1.size(); ++i)
	{
		if ( dp1[i] != '"')
			temp.push_back(dp1[i]);
	}

	return temp.compare(dp2);
}

/**
 * Get an alert by specific key
 *
 * @param    key        Key to get alert
 * @return   string     Alert
 */
std::string ManagementClient::getAlertByKey(const std::string& key)
{
	std::string response = "Status: 404 Not found";
	try
	{
		std::string url = "/fledge/alert/" + urlEncode(key) ;
		auto res = this->getHttpClient()->request("GET", url.c_str());
		std::string statusCode = res->status_code;
		if (statusCode.compare("200 OK"))
		{
			m_logger->error("Get alert failed %s.", statusCode.c_str());
			response = "Status: " + statusCode;
			return response;
		}

		response = res->content.string();
	}
	catch (const SimpleWeb::system_error &e) {
		m_logger->error("Get alert failed %s.", e.what());
	}
	return response;
}


/**
 * Raise an alert
 *
 * @param    key        Alert key
 * @param    message    Alert message
 * @param    urgency    Alert urgency
 * @return   whether operation was successful
 */
bool ManagementClient::raiseAlert(const std::string& key, const std::string& message, const std::string& urgency)
{
	try
	{
		std::string url = "/fledge/alert" ;
		ostringstream   payload;
		payload << "{\"key\":\"" << key  << "\","
					<< "\"message\":\"" << message  << "\","
					<< "\"urgency\":\"" << urgency  << "\"}";

		auto res = this->getHttpClient()->request("POST", url.c_str(), payload.str());
		std::string statusCode = res->status_code;
		if (statusCode.compare("200 OK"))
		{
			m_logger->error("Raise alert failed %s.", statusCode.c_str());
			return false;
		}

		return true;
	}
	catch (const SimpleWeb::system_error &e) {
		m_logger->error("Raise alert failed %s.", e.what());
		return false;
	}
}


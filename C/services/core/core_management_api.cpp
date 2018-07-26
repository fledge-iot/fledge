/*
 * FogLAMP core microservice management API.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <core_management_api.h>
#include <service_registry.h>
#include <rapidjson/document.h>
#include <rapidjson/writer.h>

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;
using namespace rapidjson;

CoreManagementApi *CoreManagementApi::m_instance = 0;

/**
 * Wrapper for "fake" registrer category interest
 *
 * TODO implement the missing functionality
 * This method is just a fake returning a fixed id to caller
 */
void registerInterestWrapper(shared_ptr<HttpServer::Response> response,
			     shared_ptr<HttpServer::Request> request)
{
	string payload("{\"id\" : \"1232abcd-8889-a568-0001-aabbccdd\"}");
	*response << "HTTP/1.1 200 OK\r\nContent-Length: " << payload.length() << "\r\n"
		  <<  "Content-type: application/json\r\n\r\n" << payload;
}

/**
 * Easy wrapper for getting a specific service.
 * It is called to get storage service details:
 * example: GET /foglamp/service?name=FogLAMP%20Storage
 *
 * Immediate utility is to get the management_port of
 * storage service when running tests.
 * TODO fully implemtent the getService API call
 */
void getServiceWrapper(shared_ptr<HttpServer::Response> response,
		       shared_ptr<HttpServer::Request> request)
{

	// Get QUERY STRING from request
	string queryString = request->query_string;

	size_t pos = queryString.find("name=");
	if (pos != std::string::npos)
	{
		string serviceName = queryString.substr(pos + strlen("name="));
		// replace %20 with SPACE
		serviceName = std::regex_replace(serviceName,
						 std::regex("%20"),
						 " ");
		ServiceRegistry* registry = ServiceRegistry::getInstance();
		ServiceRecord* foundService = registry->findService(serviceName);
		string payload;

		if (foundService)
		{
			// Set JSON string with service details
			// Note: the service UUID is missing at the time being
			// TODO add all API required fields
			foundService->asJSON(payload);
		}
		else
		{
			// Return not found message
			payload = "{ \"message\": \"error: service name not found\" }";
		}

		*response << "HTTP/1.1 200 OK\r\nContent-Length: " << payload.length() << "\r\n"
			  <<  "Content-type: application/json\r\n\r\n" << payload;
	}
	else
	{
		string errorMsg("{ \"message\": \"error: find service by name is supported right now\" }");
		*response << "HTTP/1.1 200 OK\r\nContent-Length: " << errorMsg.length() << "\r\n"
			  <<  "Content-type: application/json\r\n\r\n" << errorMsg;
	}
}

/**
 * Wrapper for service registration method
 */
void registerMicroServiceWrapper(shared_ptr<HttpServer::Response> response,
				 shared_ptr<HttpServer::Request> request)
{
        CoreManagementApi *api = CoreManagementApi::getInstance();
        api->registerMicroService(response, request);
}

/**
 * Wrapper for service registration method
 */
void unRegisterMicroServiceWrapper(shared_ptr<HttpServer::Response> response,
				   shared_ptr<HttpServer::Request> request)
{
        CoreManagementApi *api = CoreManagementApi::getInstance();
        api->unRegisterMicroService(response, request);
}

/**
 * Wrapper for get all categories
 */
void getAllCategoriesWrapper(shared_ptr<HttpServer::Response> response,
			     shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->getAllCategories(response, request);
}

/**
 * Wrapper for get category name
 */
void getCategoryWrapper(shared_ptr<HttpServer::Response> response,
			shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->getCategory(response, request);
}

/**
 * Wrapper for get category name
 * Also handle th special item name 'children'
 * return ing child categoriies instead of the given item
 *
 * GET /foglamp/service/category/{categoryName}/{itemName}
 * returns JSON string with item properties
 * GET /foglamp/service/category/{categoryName}/children
 * returns JSON string with child categories
 */
void getCategoryItemWrapper(shared_ptr<HttpServer::Response> response,
			    shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->getCategoryItem(response, request);
}

/**
 * Wrapper for delete a category item value
 */
void deleteCategoryItemValueWrapper(shared_ptr<HttpServer::Response> response,
				    shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->deleteCategoryItemValue(response, request);
}

/**
 * Wrapper for set category item value
 */
void setCategoryItemValueWrapper(shared_ptr<HttpServer::Response> response,
				 shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->setCategoryItemValue(response, request);
}

/**
 * Wrapper for delete category
 */
void deleteCategoryWrapper(shared_ptr<HttpServer::Response> response,
			   shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->deleteCategory(response, request);
}

/**
 * Wrapper for delete child category
 */
void deleteChildCategoryWrapper(shared_ptr<HttpServer::Response> response,
				shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->deleteChildCategory(response, request);
}

/**
 * Wrapper for create category
 */
void createCategoryWrapper(shared_ptr<HttpServer::Response> response,
			   shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->createCategory(response, request);
}

/**
 * Wrapper for create child categories
 */
void addChildCategoryWrapper(shared_ptr<HttpServer::Response> response,
			     shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->addChildCategory(response, request);
}

/**
 * Received a GET /foglamp/service/category/{categoryName}
 */
void CoreManagementApi::getCategory(shared_ptr<HttpServer::Response> response,
				    shared_ptr<HttpServer::Request> request)
{
	try
	{
		string categoryName = request->path_match[CATEGORY_NAME_COMPONENT];
		// Fetch category items
		ConfigCategory category = m_config->getCategoryAllItems(categoryName);

		// Build JSON output
		ostringstream convert;
		convert << category.itemsToJSON();

		// Send JSON data to client
		respond(response, convert.str());
	}
	catch (NoSuchCategory& ex)
	{
		// Return proper error message
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
                                    "get category",
				    ex.what());
	}
	// TODO: also catch the exceptions from ConfigurationManager
	// and return proper message
	catch (exception ex)
	{
		internalError(response, ex);
	}
}

/**
 * Received a GET /foglamp/service/category/{categoryName}/{itemName]
 */
void CoreManagementApi::getCategoryItem(shared_ptr<HttpServer::Response> response,
					shared_ptr<HttpServer::Request> request)
{
	try
	{
		string categoryName = request->path_match[CATEGORY_NAME_COMPONENT];
		string itemName = request->path_match[CATEGORY_ITEM_COMPONENT];

		if (itemName.compare("children") == 0)
		{
			// Fetch child categories
			ConfigCategories childCategories = m_config->getChildCategories(categoryName);
			// Send JSON data to client
			respond(response, "{ \"categories\" : " + childCategories.toJSON() + " }");
		}
		else
		{
			// Fetch category item
			string categoryIitem = m_config->getCategoryItem(categoryName, itemName);
			// Send JSON data to client
			respond(response, categoryIitem);
		}
	}
	// Catch the exceptions from ConfigurationManager
	// and return proper message
	catch (ChildCategoriesEx& ex)
	{
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "get child categories",
				    ex.what());
	}
	catch (NoSuchCategory& ex)
	{
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "get category item",
				    ex.what());
	}
	catch (ConfigCategoryEx& ex)
	{
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "get category item",
				    ex.what());
	}
	catch (CategoryDetailsEx& ex)
	{
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "get category item",
				    ex.what());
	}
	catch (exception ex)
	{
		internalError(response, ex);
	}
}

/**
 * Received a GET /foglamp/service/category
 */
void CoreManagementApi::getAllCategories(shared_ptr<HttpServer::Response> response,
					 shared_ptr<HttpServer::Request> request)
{
	try
	{
		// Fetch all categories
		ConfigCategories allCategories = m_config->getAllCategoryNames();

		// Build JSON output
		ostringstream convert;
		convert << "{ \"categories\" : [ ";
		convert << allCategories.toJSON();
		convert << " ] }";

		// Send JSON data to client
		respond(response, convert.str());
	}
	// TODO: also catch the exceptions from ConfigurationManager
	// and return proper message
	catch (exception ex)
	{
		internalError(response, ex);
	}
}

/**
 * Wrapper function for the default resource call.
 * This is called whenever an unrecognised entry point call is received.
 */
void defaultWrapper(shared_ptr<HttpServer::Response> response,
		    shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->defaultResource(response, request);
}


/**
 * Handle a bad URL endpoint call
 */
void CoreManagementApi::defaultResource(shared_ptr<HttpServer::Response> response,
					shared_ptr<HttpServer::Request> request)
{
	string payload("{ \"error\" : \"Unsupported URL: " + request->path + "\" }");
	respond(response,
		SimpleWeb::StatusCode::client_error_bad_request,
		payload);
}

/**
 * Construct a microservices management API manager class
 */
CoreManagementApi::CoreManagementApi(const string& name,
				     const unsigned short port) : ManagementApi(name, port)
{

	// Setup supported URL and HTTP methods
	// Services
	m_server->resource[REGISTER_SERVICE]["POST"] = registerMicroServiceWrapper;
	m_server->resource[UNREGISTER_SERVICE]["DELETE"] = unRegisterMicroServiceWrapper;

	m_server->resource[GET_SERVICE]["GET"] = getServiceWrapper;

	// Register category interest
	// TODO implement this, right now it's just a fake
	m_server->resource[REGISTER_CATEGORY_INTEREST]["POST"] = registerInterestWrapper;

	// Default wrapper
	m_server->default_resource["GET"] = defaultWrapper;
	m_server->default_resource["PUT"] = defaultWrapper;
	m_server->default_resource["POST"] = defaultWrapper;
	m_server->default_resource["DELETE"] = defaultWrapper;
	m_server->default_resource["HEAD"] = defaultWrapper;
	m_server->default_resource["CONNECT"] = defaultWrapper;

	// Set the instance
	m_instance = this;
}

/**
 * Return the singleton instance of the core management interface
 *
 * Note if one has not been explicitly created then this will
 * return 0.
 */
CoreManagementApi *CoreManagementApi::getInstance()
{
	return m_instance;
}

/**
 * Received a service registration request
 */
void CoreManagementApi::registerMicroService(shared_ptr<HttpServer::Response> response,
					     shared_ptr<HttpServer::Request> request)
{
ostringstream convert;
string uuid, payload, responsePayload;

	try {
		ServiceRegistry *registry = ServiceRegistry::getInstance();
		payload = request->content.string();

		Document doc;
		if (doc.Parse(payload.c_str()).HasParseError())
		{
		}
		else
		{
			string name, type, protocol, address;
			unsigned short port, managementPort;
			if (doc.HasMember("name"))
			{
				name = string(doc["name"].GetString());
			}
			if (doc.HasMember("type"))
			{	
				type = string(doc["type"].GetString());
			}
			if (doc.HasMember("address"))
			{
				address = string(doc["address"].GetString());
			}
			if (doc.HasMember("protocol"))
			{
				protocol = string(doc["protocol"].GetString());
			}
			if (doc.HasMember("service_port"))
			{
				port = doc["service_port"].GetUint();
			}
			if (doc.HasMember("management_port"))
			{
				managementPort = doc["management_port"].GetUint();
			}
			ServiceRecord *srv = new ServiceRecord(name,
								type,
								protocol,
								address,
								port,
								managementPort);
			if (!registry->registerService(srv))
			{
				errorResponse(response,
					      SimpleWeb::StatusCode::client_error_bad_request,
					      "register service",
					      "Failed to register service");
				return;
			}

			// Setup configuration API entry points
			if (type.compare("Storage") == 0)
			{
				/**
				 * Storage layer is registered
				 * Setup ConfigurationManager instance and URL entry points
			 	 */
				if (!getConfigurationManager(address, port))
				{
					errorResponse(response,
						      SimpleWeb::StatusCode::client_error_bad_request,
						      "ConfigurationManager",
						      "Failed to connect to storage service");
					return;
				}
				// Add Configuration Manager URL entry points
				setConfigurationEntryPoints();
			}

			// Set service uuid
			uuid = registry->getUUID(srv);
		}

		convert << "{ \"id\" : \"" << uuid << "\", ";
		convert << "\"message\" : \"Service registered successfully\"";
		convert << " }";
		responsePayload = convert.str();
		respond(response, responsePayload);
	} catch (exception ex) {
		internalError(response, ex);
	}
}

/**
 * Received a service unregister request
 */
void CoreManagementApi::unRegisterMicroService(shared_ptr<HttpServer::Response> response,
					       shared_ptr<HttpServer::Request> request)
{
ostringstream convert;

	try {
		ServiceRegistry *registry = ServiceRegistry::getInstance();
                string uuid = request->path_match[UUID_COMPONENT];

		if (registry->unRegisterService(uuid))
		{
			convert << "{ \"id\" : " << uuid << ",";
			convert << "\"message\" : \"Service unregistered successfully\"";
			convert << " }";
			string payload = convert.str();
			respond(response, payload);
		}
		else
		{
			errorResponse(response,
				      SimpleWeb::StatusCode::client_error_bad_request,
				      "unregister service",
				      "Failed to unregister service");
		}
	} catch (exception ex) {
		internalError(response, ex);
	}
}
/**
 * Send back an error response
 *
 * @param response	The HTTP Response
 * @param statusCode	The HTTP status code
 * @param entryPoint	The entry point in the API
 * @param msg		The actual error message
 */
void CoreManagementApi::errorResponse(shared_ptr<HttpServer::Response> response,
				      SimpleWeb::StatusCode statusCode,
				      const string& entryPoint,
				      const string& msg)
{
ostringstream convert;

	convert << "{ \"message\" : \"" << msg << "\", ";
	convert << "\"entryPoint\" : \"" << entryPoint << "\" }";
	respond(response, statusCode, convert.str());
}
/**
 * Handle a exception by sending back an internal error
 *
 * @param response	The HTTP response
 * @param ex		The exception that caused the error
 */
void CoreManagementApi::internalError(shared_ptr<HttpServer::Response> response,
				      const exception& ex)
{
string payload = "{ \"Exception\" : \"";

        payload = payload + string(ex.what());
        payload = payload + "\" }";

        Logger *logger = Logger::getLogger();
        logger->error("CoreManagementApi Internal Error: %s\n", ex.what());
        respond(response,
		SimpleWeb::StatusCode::server_error_internal_server_error,
		payload);
}


/**
 * HTTP response method
 */
void CoreManagementApi::respond(shared_ptr<HttpServer::Response> response,
				const string& payload)
{
        *response << "HTTP/1.1 200 OK\r\nContent-Length: " << payload.length() << "\r\n"
		  <<  "Content-type: application/json\r\n\r\n" << payload;
}

/**
 * HTTP response method
 */
void CoreManagementApi::respond(shared_ptr<HttpServer::Response> response,
				SimpleWeb::StatusCode statusCode,
				const string& payload)
{
        *response << "HTTP/1.1 " << status_code(statusCode)
		  << "\r\nContent-Length: " << payload.length() << "\r\n"
		  <<  "Content-type: application/json\r\n\r\n" << payload;
}

/**
 * Instantiate the ConfigurationManager class
 * having storage service already registered
 *
 * @return	True if ConfigurationManager is set
 *		False otherwise.
 */
bool CoreManagementApi::getConfigurationManager(const string& address,
						const unsigned short port)
{
	// Instantiate the ConfigurationManager
	if (!(m_config = ConfigurationManager::getInstance(address, port)))
	{
		return false;
	}

	Logger *logger = Logger::getLogger();
	logger->info("Storage service is connected: %s:%d\n",
		     address.c_str(),
		     port);

	return true;
}

/**
 * Add configuration manager entry points
 */
void CoreManagementApi::setConfigurationEntryPoints()
{
	// Add Configuration Manager entry points
	m_server->resource[GET_ALL_CATEGORIES]["GET"] = getAllCategoriesWrapper;
	m_server->resource[GET_CATEGORY]["GET"] = getCategoryWrapper;
	// This also hanles 'children' param for child categories
	m_server->resource[GET_CATEGORY_ITEM]["GET"] = getCategoryItemWrapper;
	m_server->resource[DELETE_CATEGORY_ITEM_VALUE]["DELETE"] = deleteCategoryItemValueWrapper;
	m_server->resource[SET_CATEGORY_ITEM_VALUE]["PUT"] = setCategoryItemValueWrapper;
	m_server->resource[DELETE_CATEGORY]["DELETE"] = deleteCategoryWrapper;
	m_server->resource[DELETE_CHILD_CATEGORY]["DELETE"] = deleteChildCategoryWrapper;
	m_server->resource[CREATE_CATEGORY]["POST"] = createCategoryWrapper;
	m_server->resource[ADD_CHILD_CATEGORIES]["POST"] = addChildCategoryWrapper;

	Logger *logger = Logger::getLogger();
	logger->info("ConfigurationManager setup is done.");
}

/**
 * Received a DELETE /foglamp/service/category/{categoryName}/{configItem}/value
 */
void CoreManagementApi::deleteCategoryItemValue(shared_ptr<HttpServer::Response> response,
						shared_ptr<HttpServer::Request> request)
{
	string categoryName = request->path_match[CATEGORY_NAME_COMPONENT];
	string itemName = request->path_match[CATEGORY_ITEM_COMPONENT];
	string value = request->path_match[ITEM_VALUE_NAME];

	try
	{
		// Unset the item value and return current updated item
		string updatedItem = m_config->deleteCategoryItemValue(categoryName,
								       itemName);
		respond(response, updatedItem);
	}
	catch (NoSuchCategoryItem& ex)
	{
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "delete category item value",
				    ex.what());
	}
        catch (exception ex)
	{
		internalError(response, ex);
	}
}

/**
 * Received PUT /foglamp/service/category/{categoryName}/{configItem}
 * Payload is {"value" : "some_data"}
 * Send to client the JSON string of category item properties
 */
void CoreManagementApi::setCategoryItemValue(shared_ptr<HttpServer::Response> response,
					     shared_ptr<HttpServer::Request> request)
{
	try
	{
		string categoryName = request->path_match[CATEGORY_NAME_COMPONENT];
		string itemName = request->path_match[CATEGORY_ITEM_COMPONENT];
		string value = request->path_match[ITEM_VALUE_NAME];

		// Get PUT data
		string payload = request->content.string();

		Document doc;
		if (doc.Parse(payload.c_str()).HasParseError() || !doc.HasMember("value"))
		{
			// Return proper error message
			this->errorResponse(response,
					    SimpleWeb::StatusCode::client_error_bad_request,
					    "set category item value",
					    "failure while parsing JSON data");
		}
		else
		{
			// TODO: it can be JSON object, tranform it to a string
			string theValue = doc["value"].GetString();

			// Set the new value
			if (!m_config->setCategoryItemValue(categoryName,
							     itemName,
							     theValue))
			{
				// Return proper error message
				this->errorResponse(response,
						    SimpleWeb::StatusCode::client_error_bad_request,
						    "set category item value",
						    "failure while writing to storage layer");
			}
			else
			{
				// Send JSON data
				this->respond(response,
					      m_config->getCategoryItem(categoryName,
									itemName));
			}
		}
	}
	catch(NoSuchCategoryItem& ex)
	{
		// Return proper error message
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "set category item value",
				    ex.what());
	}
	catch (exception ex)
	{
		internalError(response, ex);
	}
}

/**
 * Delete a config category
 * Received DELETE /foglamp/service/category/{categoryName}
 * Send to client the JSON string of all remaining categories
 */
void CoreManagementApi::deleteCategory(shared_ptr<HttpServer::Response> response,
				       shared_ptr<HttpServer::Request> request)
{
	try
	{
		string categoryName = request->path_match[CATEGORY_NAME_COMPONENT];
		ConfigCategories updatedCategories = m_config->deleteCategory(categoryName);

		this->respond(response,
			      "{ \"categories\" : " + updatedCategories.toJSON() + " }");
		return;
	}
	catch (NoSuchCategory& ex)
	{
		// Return proper error message
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "delete category",
				    ex.what());
	}
	catch (exception ex)
	{
		internalError(response, ex);
	}
}

/**
 * Delete child categories of a config category
 * Received DELETE /foglamp/service/category/{categoryName}/children/{childCategory}
 * Send to client the JSON string of all remaining categories
 */
void CoreManagementApi::deleteChildCategory(shared_ptr<HttpServer::Response> response,
					    shared_ptr<HttpServer::Request> request)
{
	try
	{
		string categoryName = request->path_match[CATEGORY_NAME_COMPONENT];
		string childCategoryName = request->path_match[CHILD_CATEGORY_COMPONENT];

		// Remove selecte child cateogry fprm parent category
		string updatedChildren = m_config->deleteChildCategory(categoryName,
								       childCategoryName);
		this->respond(response, updatedChildren);
	}
	catch (ChildCategoriesEx& ex)
	{
		// Return proper error message
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "delete child category",
				    ex.what());
	}
	catch (exception ex)
	{
		internalError(response, ex);
	}
}

/**
 * Create a new configuration category
 * Received POST /foglamp/service/category
 *
 * Send to client the JSON string of new category's items
 */
void CoreManagementApi::createCategory(shared_ptr<HttpServer::Response> response,
				       shared_ptr<HttpServer::Request> request)
{
	try
	{
		bool keepOriginalItems = false;

		// Get query_string
		string queryString = request->query_string;

		size_t pos = queryString.find("keep_original_items");
		if (pos != std::string::npos)
		{
			string paramValue = queryString.substr(pos + strlen("keep_original_items="));

			for (auto &c: paramValue) c = tolower(c);

			if (paramValue.compare("true") == 0)
			{
				keepOriginalItems = true;
			}	
		}

		// Get POST data
		string payload = request->content.string();

                Document doc;
		if (doc.Parse(payload.c_str()).HasParseError() ||
		    !doc.HasMember("key") ||
		    !doc.HasMember("description") ||
		    !doc.HasMember("value") ||
		    // It must be an object
		    !doc["value"].IsObject() ||
		    // It must be a string
		    !doc["key"].IsString() ||
		    // It must be a string
		    !doc["description"].IsString())
		{
			// Return proper error message
			this->errorResponse(response,
					    SimpleWeb::StatusCode::client_error_bad_request,
					    "create category",
					    "failure while parsing JSON data");
			return;
		}

		// Get the JSON input properties
		string categoryName = doc["key"].GetString();
		string categoryDescription = doc["description"].GetString();
		const Value& categoryItems = doc["value"];

		// Create string representation of JSON object
		rapidjson::StringBuffer buffer;
		rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
		categoryItems.Accept(writer);
		const string sItems(buffer.GetString(), buffer.GetSize());

		// Create the new config category
		ConfigCategory items = m_config->createCategory(categoryName,
								categoryDescription,
								sItems,
								keepOriginalItems);

		// Return JSON string of the new created category
		this->respond(response, items.toJSON());
	}
	catch (ConfigCategoryDefaultWithValue& ex)
	{
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "create category",
				    ex.what());
	}
	catch (ConfigCategoryEx ex)
	{
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "create category",
				    ex.what());
	}
	catch (CategoryDetailsEx ex)
	{
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "create category",
				    ex.what());
	}
	catch (exception ex)
	{
		internalError(response, ex);
	}
}

/**
 * Add child categories to a given category name
 * Received POST /foglamp/service/category/{categoryName}/children
 *
 * Send to client the JSON string with child categories
 */
void CoreManagementApi::addChildCategory(shared_ptr<HttpServer::Response> response,
					 shared_ptr<HttpServer::Request> request)
{
	try
	{
		// Get categopryName
		string categoryName = request->path_match[CATEGORY_NAME_COMPONENT];
		// Get POST data
		string childCategories = request->content.string();

                Document doc;
		if (doc.Parse(childCategories.c_str()).HasParseError() ||
		    // It must be an object
		    !doc.IsObject())
		{
			// Return proper error message
			this->errorResponse(response,
					    SimpleWeb::StatusCode::client_error_bad_request,
					    "add child category",
					    "failure while parsing JSON data");
			return;
		}

		// Add new child categories and return all child items JSON list
		this->respond(response,
			      m_config->addChildCategory(categoryName,
							 childCategories));
	}
	catch (ExistingChildCategories& ex)
	{
		// Return proper error message
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "add child category",
				    ex.what());
	}
	catch (NoSuchCategory& ex)
	{
		// Return proper error message
		this->errorResponse(response,
				    SimpleWeb::StatusCode::client_error_bad_request,
				    "add child category",
				    ex.what());
	}
	catch (exception ex)
	{
		internalError(response, ex);
	}
}

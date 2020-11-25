#include <MDNSDiscovery.h>
#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <string.h>
#include <vector>

using namespace std;
using namespace rapidjson;

/**
 * The MDNS discovery class constructor
 *
 * @param service	The service name to discover
 */
MDNSDiscovery::MDNSDiscovery(const string& service) : m_service(service)
{
}

/**
 * The MDNS discovery class destructor
 */
MDNSDiscovery::~MDNSDiscovery()
{
}

/**
 * Do an DMDNS service discovery and add the discovered 
 * IP addresses to the configuration category passed in 
 * the parameter config.
 *
 * Use the item naem passed in item to populate the lsit. The
 * item must be an enumeration, each IP address is added as 
 * an option to the enumeration.
 *
 * @param config	The JSON configuration as a string
 * @param item		The item name to populate
 * @return The new configuraton category as a string
 */
char *MDNSDiscovery::discover(const char *config, const char *item)
{
Document doc;
vector<Zeroconf::mdns_responce> result;

	doc.Parse(config);
	Document::AllocatorType& allocator = doc.GetAllocator();
	if (Zeroconf::Resolve(service.c_str(), 5, &result))
	{
		Value options(kArrayType);
		char def[INET6_ADDRSTRLEN + 1] = {0};
		for (size_t i = 0; i < result.size(); i++)
    		{
			auto entry = result[i];
			char buffer[INET6_ADDRSTRLEN + 1] = {0};
			inet_ntop(entry.peer.ss_family, get_in_addr(&entry.peer), buffer, INET6_ADDRSTRLEN);
			Value addr;
			addr.SetString(buffer, strlen(buffer), allocator);
			options.PushBack(addr, allocator);
			if (i == 0)
			{
				strncpy(def, buffer, INET6_ADDRSTRLEN+1);
			}
		}
		Value &addr_item = doc[item];
		addr_item.AddMember("options", options, allocator);
		addr_item["default"].SetString(def, strlen(def), allocator);
	}
	else
	{
		Logger::getLogger()->warn("No devices offering the servier '%s' have been found", m_service.c_str());
		Value &addr_item = doc[item];
		addr_item["type"].SetString("string", 6, allocator);
	}

	StringBuffer buffer;
	Writer<StringBuffer> writer(buffer);
	doc.Accept(writer);

	return strdup(buffer.GetString());
}

void *FlirDiscovery::get_in_addr(sockaddr_storage* sa)
{
	if (sa->ss_family == AF_INET)
		return &reinterpret_cast<sockaddr_in*>(sa)->sin_addr;
	if (sa->ss_family == AF_INET6)
		return &reinterpret_cast<sockaddr_in6*>(sa)->sin6_addr;
	return nullptr;
}

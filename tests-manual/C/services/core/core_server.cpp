#include <core_management_api.h>
#include <configuration_manager.h>
#include <rapidjson/document.h>
#include <service_registry.h>

int main(int argc, char** argv)
{
	unsigned short port = 9393;
	if (argc == 2 && argv[1])
	{
		port = (unsigned short)atoi(argv[1]);
	}

	// Instantiate CoreManagementApi class
	CoreManagementApi coreServer("test_core", port);

	// Start the core server
	CoreManagementApi::getInstance()->startServer();
}

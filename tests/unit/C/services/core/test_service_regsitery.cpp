#include <gtest/gtest.h>
#include <service_registry.h>

using namespace std;

TEST(ServiceRegistryTest, Creation)
{
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	ASSERT_NE(registry, (ServiceRegistry *)0);
}

TEST(ServiceRegistryTest, Singleton)
{
	ServiceRegistry *registry1 = ServiceRegistry::getInstance();
	ServiceRegistry *registry2 = ServiceRegistry::getInstance();
	ASSERT_EQ(registry1, registry2);
}

TEST(ServiceRegistryTest, Register)
{
EXPECT_EXIT({
	ServiceRecord *record = new ServiceRecord("test1", "south", "http", "hostname", 1234, 4321);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	bool ret = registry->registerService(record);
	if (!ret)
	{
		cerr << "registerService 'test1' returned false" << endl;
		exit(1);
	}
	exit(!(ret == true)); }, ::testing::ExitedWithCode(0), "");
}

TEST(ServiceRegistryTest, DupRegister)
{
EXPECT_EXIT({
	ServiceRecord *record = new ServiceRecord("test1", "south", "http", "hostname", 1234, 4321);
	ServiceRecord *dupRecord = new ServiceRecord("test1", "north", "http", "hostname", 1234, 4321);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	bool ret = registry->registerService(record);
	if (!ret)
	{
		cerr << "Failed to register 'test1'" << endl;
		exit(1);
	}
	ret = registry->registerService(dupRecord);
	if (ret)
	{
		cerr << "Registering 'test1' twice does not return false" << endl;
	}
	exit(!(ret == false)); }, ::testing::ExitedWithCode(0), "");
}

TEST(ServiceRegistryTest, Overwrite)
{
EXPECT_EXIT({
	ServiceRecord *record = new ServiceRecord("test1", "south", "http", "hostname", 1234, 4321);
	ServiceRecord *dupRecord = new ServiceRecord("test1", "south", "http", "hostname", 1234, 666);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	bool ret = registry->registerService(record);
	if (!ret)
	{
		cerr << "Failed to register 'test1'" << endl;
		exit(1);
	}
	ret = registry->registerService(dupRecord);
	if (!ret)
	{
		cerr << "Failed to overwite 'test1'" << endl;
	}
	exit(!(ret == true)); }, ::testing::ExitedWithCode(0), "");
}

TEST(ServiceRegistryTest, Find)
{
EXPECT_EXIT({
	ServiceRecord *record = new ServiceRecord("findtest", "south", "http", "hostname", 1234, 4321);
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	bool ret = registry->registerService(record);
	if (!ret)
	{
		cerr << "Failed to register 'findtest'" << endl;
		exit(1);
	}
	record = registry->findService("findtest");
	if (record == (ServiceRecord *)0)
	{
		cerr << "findService 'findtest' can not be NULL" << endl;
	}
	exit(!record); }, ::testing::ExitedWithCode(0), "");
}

TEST(ServiceRegistryTest, NotFind)
{
EXPECT_EXIT({
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	ServiceRecord* record = registry->findService("non-existant");
	if (record != (ServiceRecord *)0)
	{
		cerr << "findService 'non-existant' must return NULL" << endl;
	}
	exit(!(record == (ServiceRecord *)0)); }, ::testing::ExitedWithCode(0), "");
}

TEST(ServiceRegistryTest, Unregister)
{
EXPECT_EXIT({
	ServiceRecord *record = new ServiceRecord("unregisterme", "south", "http", "hostname", 1234, 4321);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	bool ret = registry->registerService(record);
	if (!ret)
	{
		cerr << "registerService 'unregisterme' failed" << endl;
		exit(1);
	}
	ret = registry->unRegisterService(record);
	if (!ret)
	{
		cerr << "unRegisterService 'unregisterme' failed" << endl;
	}
	exit(!(ret == true)); }, ::testing::ExitedWithCode(0), "");
}

TEST(ServiceRegistryTest, UnregisterNoExistant)
{
EXPECT_EXIT({
	ServiceRecord *record = new ServiceRecord("non-existant", "north", "http", "hostname", 1234, 4321);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	bool ret = registry->unRegisterService(record);
	if (ret)
	{
		cerr << "unRegisterService 'non-existant' failed" << endl;
	}
	exit(!(ret == false)); }, ::testing::ExitedWithCode(0), "");
}

TEST(ServiceRegistryTest, uuid)
{
EXPECT_EXIT({
	ServiceRecord *record = new ServiceRecord("testuuid", "south", "http", "hostname", 1234, 4321);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	bool ret = registry->registerService(record);
	if (!ret)
	{
		cerr << "registerService 'testuuid' failed" << endl;
		exit(1);
	}
	string uuid = registry->getUUID(record);
	ret = registry->unRegisterService(uuid);
	if (!ret)
	{
		cerr << "unRegisterService 'testuuid' by UUID failed" << endl;
	}
	exit(!(ret == true)); }, ::testing::ExitedWithCode(0), "");
}


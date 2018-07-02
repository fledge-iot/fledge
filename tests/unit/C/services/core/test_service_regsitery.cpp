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
	ServiceRecord *record = new ServiceRecord("test1", "south", "http", "hostname", 1234, 4321);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	ASSERT_EQ(registry->registerService(record), true);
}

TEST(ServiceRegistryTest, DupRegister)
{
	ServiceRecord *record = new ServiceRecord("test1", "south", "http", "hostname", 1234, 4321);
	ServiceRecord *dupRecord = new ServiceRecord("test1", "north", "http", "hostname", 1234, 4321);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	ASSERT_EQ(registry->registerService(record), true);
	ASSERT_EQ(registry->registerService(dupRecord), false);
}

TEST(ServiceRegistryTest, Overwrite)
{
	ServiceRecord *record = new ServiceRecord("test1", "south", "http", "hostname", 1234, 4321);
	ServiceRecord *dupRecord = new ServiceRecord("test1", "south", "http", "hostname", 1234, 666);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	ASSERT_EQ(registry->registerService(record), true);
	ASSERT_EQ(registry->registerService(dupRecord), true);
}

TEST(ServiceRegistryTest, Find)
{
	ServiceRecord *record = new ServiceRecord("findtest", "south", "http", "hostname", 1234, 4321);
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	ASSERT_EQ(registry->registerService(record), true);
	ASSERT_NE(registry->findService("findtest"), (ServiceRecord *)0);
}

TEST(ServiceRegistryTest, NotFind)
{
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	ASSERT_EQ(registry->findService("non-existant"), (ServiceRecord *)0);
}

TEST(ServiceRegistryTest, Unregister)
{
	ServiceRecord *record = new ServiceRecord("unregisterme", "south", "http", "hostname", 1234, 4321);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	ASSERT_EQ(true, registry->registerService(record));
	ASSERT_EQ(true, registry->unRegisterService(record));
}

TEST(ServiceRegistryTest, UnregisterNoExistant)
{
	ServiceRecord *record = new ServiceRecord("non-existant", "north", "http", "hostname", 1234, 4321);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	ASSERT_EQ(registry->unRegisterService(record), false);
}

TEST(ServiceRegistryTest, uuid)
{
	ServiceRecord *record = new ServiceRecord("testuuid", "south", "http", "hostname", 1234, 4321);
	
	ServiceRegistry *registry = ServiceRegistry::getInstance();
	ASSERT_EQ(registry->registerService(record), true);
	string uuid = registry->getUUID(record);
	ASSERT_EQ(true, registry->unRegisterService(uuid));
}


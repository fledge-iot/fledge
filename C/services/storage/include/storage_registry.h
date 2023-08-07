#ifndef _STORAGE_REGISTRY_H
#define _STORAGE_REGISTRY_H

#include <vector>
#include <queue>
#include <string>
#include <mutex>
#include <condition_variable>
#include <thread>

typedef std::vector<std::pair<std::string *, std::string *> > REGISTRY;

typedef struct {
	std::string url;
	std::string key;
	std::vector<std::string> keyValues;
	std::string operation;
} TableRegistration;

typedef std::vector<std::pair<std::string *, TableRegistration *> > REGISTRY_TABLE;


/**
 * StorageRegistry - a class that manages requests from other microservices
 * to register interest in new readings being inserted into the storage layer
 * that match a given asset code, or any asset code "*".
 */
class StorageRegistry {
	public:
		StorageRegistry();
		~StorageRegistry();
		void		registerAsset(const std::string& asset, const std::string& url);
		void		unregisterAsset(const std::string& asset, const std::string& url);
		void		process(const std::string& payload);
		void		processTableInsert(const std::string& tableName, const std::string& payload);
		void		processTableUpdate(const std::string& tableName, const std::string& payload);
		void		processTableDelete(const std::string& tableName, const std::string& payload);
		void		registerTable(const std::string& table, const std::string& url);
		void		unregisterTable(const std::string& table, const std::string& url);
		void		run();
	private:
		void		processPayload(char *payload);
		void		sendPayload(const std::string& url, const char *payload);
		void		filterPayload(const std::string& url, char *payload, const std::string& asset);
		void		processInsert(char *tableName, char *payload);
		void		processUpdate(char *tableName, char *payload);
		void		processDelete(char *tableName, char *payload);
		TableRegistration*
				parseTableSubscriptionPayload(const std::string& payload);
		void 		insertTestTableReg();
		void		removeTestTableReg(int n);
        
		typedef 	std::pair<time_t, char *> Item;
		typedef 	std::tuple<time_t, char *, char *> TableItem;
		REGISTRY			m_registrations;
		REGISTRY_TABLE			m_tableRegistrations;
        
		std::queue<StorageRegistry::Item>
						m_queue;
		std::queue<StorageRegistry::TableItem>
						m_tableInsertQueue;
		std::queue<StorageRegistry::TableItem>
						m_tableUpdateQueue;
		std::queue<StorageRegistry::TableItem>
						m_tableDeleteQueue;
		std::mutex			m_qMutex;
		std::mutex			m_registrationsMutex;
		std::mutex			m_tableRegistrationsMutex;
		std::thread			*m_thread;
		std::condition_variable		m_cv;
		std::mutex			m_cvMutex;
		bool				m_running;
};

#endif

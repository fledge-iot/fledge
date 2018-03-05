#ifndef _INGEST_H
#define _INGEST_H
/*
 * FogLAMP reading ingest.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <storage_client.h>
#include <reading.h>
#include <vector>
#include <thread>
#include <mutex>

/**
 */
class Ingest {

public:
	Ingest(StorageClient& storage);
	~Ingest();

	void		ingest(const Reading& reading);
	bool		running();
	void		processQueue();

private:
	StorageClient&		m_storage;
	bool			m_running;
	std::vector<Reading *>	*m_queue;
	std::mutex		m_qMutex;
	std::thread		*m_thread;
};

#endif

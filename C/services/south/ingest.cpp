/*
 * FogLAMP readings ingest.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <ingest.h>
#include <reading.h>
#include <chrono>
#include <thread>

using namespace std;

void ingestThread(Ingest *ingest)
{
	while (ingest->running())
	{
		this_thread::sleep_for(chrono::milliseconds(2000));
		ingest->processQueue();
	}
}

Ingest::Ingest(StorageClient& storage) : m_storage(storage)
{
	m_running = true;
	m_queue = new vector<Reading *>();
	m_thread = new thread(ingestThread, this);
}

Ingest::~Ingest()
{
	m_running = false;
	m_thread->join();
	processQueue();
	delete m_queue;
	delete m_thread;
}

bool Ingest::running()
{
	return m_running;
}

void Ingest::ingest(const Reading& reading)
{
	lock_guard<mutex> guard(m_qMutex);
	m_queue->push_back(new Reading(reading));
	
}

void Ingest::processQueue()
{
}

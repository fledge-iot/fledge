/*
 * Fledge storage service client
 *
 * Copyright (c) 2023 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <perfmonitors.h>
#include <chrono>

using namespace std;

/**
 * Constructor for an individual performance monitor
 *
 * @param name	The name of the performance monitor
 */
PerfMon::PerfMon(const string& name) : m_name(name), m_samples(0)
{
}

/**
 * Collect a new value for the performance monitor
 *
 * @param value	The new value
 */
void PerfMon::addValue(long value)
{
	lock_guard<mutex> guard(m_mutex);
	if (m_samples)
	{
		if (value < m_min)
			m_min = value;
		else if (value > m_max)
			m_max = value;
		m_average = ((m_samples * m_average) + value) / (m_samples + 1);
		m_samples++;
	}
	else
	{
		m_min = value;
		m_max = value;
		m_average = value;
		m_samples = 1;
	}
}

/**
 * Return the performance values to insert
 *
 */
int PerfMon::getValues(InsertValues& values)
{
	lock_guard<mutex> guard(m_mutex);
	if (m_samples == 0)
		return 0;
	values.push_back(InsertValue("minimum", m_min));
	values.push_back(InsertValue("maximum", m_max));
	values.push_back(InsertValue("average", m_average));
	values.push_back(InsertValue("samples", m_samples));
	m_min = 0;
	m_max = 0;
	m_average = 0;
	int samples = m_samples;
	m_samples = 0;
	return samples;
}

/**
 * Constructor for the performance monitors
 *
 * @param service	The name of the service
 * @param storage	Point to the storage client class for the service
 */
PerformanceMonitor::PerformanceMonitor(const string& service, StorageClient *storage) :
	m_service(service), m_storage(storage), m_collecting(false), m_task(NULL)
{
}

/**
 * Destructor for the performance monitor
 */
PerformanceMonitor::~PerformanceMonitor()
{
	if (m_collecting)
	{
		setCollecting(false);
	}
	if (m_task)
	{
		HouseKeeper *hk = HouseKeeper::getInstance();
		hk->removeTask(m_task);
		delete m_task;
		m_task = NULL;
	}
	// Write task has now been stopped or
	// was never running
	for (const auto& it : m_monitors)
	{
		string name = it.first;
		PerfMon *mon = it.second;
		delete mon;
	}
}


/**
 * Set the collection state of the performance monitors
 *
 * @param state	The required collection state
 */
void PerformanceMonitor::setCollecting(bool state)
{
	HouseKeeper *hk = HouseKeeper::getInstance();
	m_collecting = state;
	if (m_collecting && m_task == NULL)
	{
		// Start the thread to write the monitors to the database
		m_task = new PerformanceTask(this);
		hk->addTask(m_task);
	}
	else if (m_collecting == false && m_task)
	{
		hk->removeTask(m_task);
		delete m_task;
		m_task = NULL;
	}
}

/**
 * Add a new value to the named performance monitor
 *
 * @param name	The name of the performance monitor
 * @param value	The value to add
 */
void PerformanceMonitor::doCollection(const string& name, long value)
{
	PerfMon *mon;
	auto it = m_monitors.find(name);
	if (it == m_monitors.end())
	{
		// Create a new monitor
		mon = new PerfMon(name);
		m_monitors[name] = mon;
	}
	else
	{
		mon = it->second;
	}
	mon->addValue(value);
}

/**
 * The housekeeper task that runs to write database values
 */
void PerformanceMonitor::writeCounters()
{
	unique_lock<mutex> lk(m_mutex);
	if (m_collecting)
	{
		// Write to the database
		for (const auto& it : m_monitors)
		{
			string name = it.first;
			PerfMon *mon = it.second;
			InsertValues values;
			if (mon->getValues(values) > 0)
			{
				values.push_back(InsertValue("service", m_service));
				values.push_back(InsertValue("monitor", name));
				m_storage->insertTable("monitors", values);
			}
		}
	}
}

/**
 * Constructor for the house keeper task used to write
 * the performance monitors to the database.
 *
 * We arrange for the run method to be called every 60 seconds
 *
 * @param monitor	The performance monitor instance
 */
PerformanceTask::PerformanceTask(PerformanceMonitor *monitor) :
	m_monitor(monitor), HouseKeeperTask("PerformanceMonitor", 60)
{
}

/**
 * The run routine called every 60 seconds by the house keeper. Simply
 * write the performance counters to the database.
 */
void PerformanceTask::run()
{
	m_monitor->writeCounters();
}

/**
 * The cleanup routine called either when the housekeeper shuts down
 * or the task is removed from the house keeper list of tasks.
 */
void PerformanceTask::cleanup()
{
	// Do nothing. We don't want to write a partial minutes worth of data
}

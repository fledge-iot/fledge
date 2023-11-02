/*
 * Fledge Singleton House Keeper thread
 *
 * Copyright (c) 2023 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <housekeeper.h>

HouseKeeper *HouseKeeper::m_instance = 0;

using namespace std;

/**
 * Run the housekeeper thread
 *
 * @param hk	The housekeeper instance
 */
static void hkThread(HouseKeeper *hk)
{
	hk->runTasks();
}

/**
 * Return the singleton Housekeeper instance
 */
HouseKeeper *HouseKeeper::getInstance()
{
	if (! m_instance)
	{
		m_instance = new HouseKeeper();
	}
	return m_instance;
}

/**
 * Construct the housekeeper class.
 *
 * We don't start any threads until something is queued
 */
HouseKeeper::HouseKeeper() : m_thread(NULL), m_nextTask(NULL)
{
	m_logger = Logger::getLogger();
}

/**
 * Destroy the house keeper instance
 *
 * Shutdown the thread and call the cleanup() routine for any
 * housekeeper tasks that are registered.
 */
HouseKeeper::~HouseKeeper()
{
	m_logger->warn("Housekeeper shutdown in progress");
	lock_guard<mutex> guard(m_mutex);
	for (auto& task : m_tasks)
	{
		task->cleanup();
		delete task;
	}
	// Prevent any threads from running
	m_tasks.clear();
	m_nextTask = NULL;

	// Wakeup the thread if it is running
	m_shutdown = true;
	m_cv.notify_all();
	if (m_thread)
	{
		m_thread->join();
		delete m_thread;
		m_thread = NULL;
	}
}

/**
 * Add a new task to the list of registered tasks for the 
 * housekeeper to run.
 *
 * @param task	The task to add
 */
void HouseKeeper::addTask(HouseKeeperTask *task)
{
	m_logger->info("Housekeeper add task %s", task->getName().c_str());
	lock_guard<mutex> guard(m_mutex);
	m_tasks.push_back(task);
	findNextTask();			// The next task might have changed
	if (m_thread == NULL)
	{
		// Start the thread if it is not running
		m_shutdown = false;
		m_thread = new thread(hkThread, this);
	}
	// Wakeup the thread so that it may schedule the next task
	m_cv.notify_all();
}

/**
 * Remove a registered task from the house keeper queue
 *
 * If a task is found then the cleanup of the task is called.
 * Note: the task is not deleted by this routine and the caller
 * must delete the task.
 *
 * @param task	The task to remove
 */
void HouseKeeper::removeTask(HouseKeeperTask *task)
{
	m_logger->info("Housekeeper remove task %s", task->getName().c_str());
	lock_guard<mutex> guard(m_mutex);
	for (auto it = m_tasks.begin(); it != m_tasks.end(); it++)
	{
		if (*it == task)
		{
			m_logger->fatal("Found task to remove");
			task->cleanup();
			m_tasks.erase(it);
			break;
		}
	}
	// Wakeup the thread so that it may schedule the next task
	m_cv.notify_all();
}

/**
 * Find the next task to execute. Based on the next execution time
 * and the priority this routine will get the m_nextTask member
 * variable to the next task that should be run.
 *
 * Note: This routine expects to be called with m_mutex held by 
 * the caller
 */
void HouseKeeper::findNextTask()
{
	if (m_tasks.size())
	{
		m_nextTask = m_tasks[0];
		time_t	bestTime = m_nextTask->getNextExecution();
		HKPriority bestPriority = m_nextTask->getPriority();
		for (auto& candidate : m_tasks)
		{
			if (candidate->getNextExecution() < bestTime)
			{
				m_nextTask = candidate;
				bestTime = m_nextTask->getNextExecution();
				bestPriority = m_nextTask->getPriority();
			}
			else if (candidate->getNextExecution() == bestTime)
			{
				if ((bestPriority == HK_NORMAL || bestPriority == HK_LOW) && candidate->getPriority() == HK_HIGH)
				{
					m_nextTask = candidate;
					bestTime = m_nextTask->getNextExecution();
					bestPriority = m_nextTask->getPriority();
				}
				else if (bestPriority == HK_LOW && candidate->getPriority() == HK_NORMAL)
				{
					m_nextTask = candidate;
					bestTime = m_nextTask->getNextExecution();
					bestPriority = m_nextTask->getPriority();
				}
			}
		}
	}
	else
	{
		m_nextTask = NULL;
	}
}

/**
 * The thread of the housekeeper. This runs until the m_shutdown flag is
 * set. It looks for tasks to run and exeutes them, waiting on a condition
 * varaible until there might be a task to run.
 */
void HouseKeeper::runTasks()
{
	std::unique_lock<std::mutex> lk(m_mutex);
	do {
		// Check if we are woken by a task that is ready to be run
		if (m_nextTask && m_nextTask->getNextExecution() <= time(0))
		{
			HouseKeeperTask *task = m_nextTask;
			lk.unlock();
			m_logger->debug("Housekeeper running task %s", task->getName().c_str());
			task->run();
			if (task->setNextExecution() == 0L)
			{
				removeTask(task);
			}
			lk.lock();
		}

		// Find the next task to run if any
		findNextTask();

		if (m_nextTask)
		{
			// Wait until it is time to run another task
			// or a new task is registered.
			m_cv.wait_for(lk, chrono::seconds(m_nextTask->getNextExecution() - time(0)));
		}
		else
		{
			// There is nothing to run, so sleep until woken up
			// when a new task is registered
			m_cv.wait(lk);
		}
	} while (m_shutdown == false);
    
}

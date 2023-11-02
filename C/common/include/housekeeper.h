#ifndef _HOUSEKEEPER_H
#define _HOUSEKEEPER_H
/*
 * Fledge storage client.
 *
 * Copyright (c) 2023 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <logger.h>
#include <vector>
#include <thread>
#include <condition_variable>

class HouseKeeperTask;

/**
 * A single class that implements a house keeper thread that is used
 * to run periodic or one-off tasks on a separate thread. The purpose
 * of the house keeper is to reduce the number of threads that are run
 * in order to reduce both the meomry footprint and the quantity of threads
 * in the system.
 *
 * The housekeeper should be used for any task that needs to be run on a
 * periodic basis but does not require to run for long each time it runs. Likewise
 * it may be used to run occasional one-off tasks on a separate thread, again
 * these one-off tasks should not run for any considerable amount of time
 * as they may block other periodic tasks.
 */
class HouseKeeper {
	public:
		~HouseKeeper();
		static HouseKeeper	*getInstance();
		static HouseKeeper	*m_instance;
		void			addTask(HouseKeeperTask *task);
		void			removeTask(HouseKeeperTask *task);
		void			runTasks();
	private:
		void			findNextTask();
	private:
		HouseKeeper();
		Logger			*m_logger;
		std::thread		*m_thread;
		std::vector<HouseKeeperTask *>
					m_tasks;
		HouseKeeperTask		*m_nextTask;
		std::mutex		m_mutex;
		std::condition_variable	m_cv;
		bool			m_shutdown;
};

/**
 * Housekeeper priorities used when two house keeper tasks should run
 * at the same time.
 */
typedef enum {
	/**
	 * Low priority task whose execution is not time critical and can
	 * wait for other tasks to complete.
	 */
	HK_LOW,
	/**
	 * A normal priority task that should be run if possible on the
	 * schedule given but that is not critical.
	 */
       	HK_NORMAL,
	/**
	 * A task that must be run as close as possible to the time interval
	 * given.
	 */
	HK_HIGH
} HKPriority;

/**
 * The generic house keeper task that is run by the house keeper thread
 *
 * Users of the house keeper must be derived from this class and supply
 * a run and a cleanup routine. The run is executed each time the housekeeper
 * runs the task and the cleanup is called when the house keeper is shutdown
 * or when the task is run for the final time.
 */
class HouseKeeperTask {
	public:
		HouseKeeperTask(const std::string& name, int repeat = 0, HKPriority priority = HK_NORMAL) :
					m_name(name), m_repeat(repeat), m_priority(priority)
					{
						m_nextExecution = time(0) + repeat;
					};
		virtual 		~HouseKeeperTask() {};
		virtual void 		run() = 0;
		virtual void		cleanup() = 0;

					/**
					 * Return the next execution time for the task
					 */
		time_t			getNextExecution() { return m_nextExecution; };

					/**
					 * Get the priority of the house keeper task
					 */
		HKPriority		getPriority() { return m_priority; };
					/**
					 * Set the time for the next execution of the task.
					 * If the task is not to be repeated then a 0 value
					 * is returned.
					 */
		time_t			setNextExecution()
					{
						if (m_repeat)
							m_nextExecution = time(0) + m_repeat;
						else
							m_nextExecution = 0;
						return m_nextExecution;
					}

					/**
					 * Return the name of the task
					 */
		std::string		getName() { return m_name; };
	private:
		std::string		m_name;
		int			m_repeat;
		HKPriority		m_priority;
		time_t			m_nextExecution;
};
#endif

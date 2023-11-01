#include <gtest/gtest.h>
#include <string>
#include <vector>
#include <chrono>
#include <thread>
#include "housekeeper.h"

using namespace std;

class counterTask : public HouseKeeperTask {
	public:
		counterTask(const std::string name, int repeat = 0, HKPriority priority = HK_NORMAL) :
			HouseKeeperTask(name, repeat, priority)
		{
			m_count = 0;
			m_cleanup = 0;
		}

		int getCount() { return m_count; };
		int getCleanup() { return m_cleanup; };

		void run()
		{
			m_count++;
		};
		void cleanup()
		{
			m_cleanup++;
		};
	private:
		int	m_count;
		int	m_cleanup;
};

TEST(HouseKeeper, OneOff)
{
HouseKeeper *hk = HouseKeeper::getInstance();
counterTask *task = new counterTask("OneOff");

	hk->addTask(task);
	this_thread::sleep_for(chrono::milliseconds(2000));

	ASSERT_EQ(task->getCount(), 1);
	ASSERT_EQ(task->getCleanup(), 1);
	delete task;
}

TEST(HouseKeeper, Repeated)
{
HouseKeeper *hk = HouseKeeper::getInstance();
counterTask *task = new counterTask("2seconds", 2);

	hk->addTask(task);
	this_thread::sleep_for(chrono::milliseconds(2500));
	ASSERT_EQ(task->getCount(), 1);
	ASSERT_EQ(task->getCleanup(), 0);
	this_thread::sleep_for(chrono::milliseconds(1600));
	ASSERT_EQ(task->getCount(), 2);
	ASSERT_EQ(task->getCleanup(), 0);
	hk->removeTask(task);
	ASSERT_EQ(task->getCleanup(), 1);
}

TEST(HouseKeeper, TestRepeated)
{
HouseKeeper *hk = HouseKeeper::getInstance();
counterTask *task = new counterTask("2seconds", 2);

	hk->addTask(task);
	this_thread::sleep_for(chrono::milliseconds(6500));
	ASSERT_EQ(task->getCount(), 3);
	ASSERT_EQ(task->getCleanup(), 0);
	hk->removeTask(task);
	ASSERT_EQ(task->getCleanup(), 1);
}

TEST(HouseKeeper, TwoTsaks)
{
HouseKeeper *hk = HouseKeeper::getInstance();
counterTask *task1 = new counterTask("2seconds", 2);
counterTask *task2 = new counterTask("4seconds", 4);

	hk->addTask(task1);
	hk->addTask(task2);
	this_thread::sleep_for(chrono::milliseconds(2500));
	ASSERT_EQ(task1->getCount(), 1);
	ASSERT_EQ(task1->getCleanup(), 0);
	ASSERT_EQ(task2->getCount(), 0);
	ASSERT_EQ(task2->getCleanup(), 0);
	this_thread::sleep_for(chrono::milliseconds(2000));
	ASSERT_EQ(task1->getCount(), 2);
	ASSERT_EQ(task1->getCleanup(), 0);
	ASSERT_EQ(task2->getCount(), 1);
	ASSERT_EQ(task2->getCleanup(), 0);
	hk->removeTask(task1);
	hk->removeTask(task2);
	ASSERT_EQ(task1->getCleanup(), 1);
	ASSERT_EQ(task2->getCleanup(), 1);
}

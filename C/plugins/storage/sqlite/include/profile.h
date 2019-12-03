#ifndef _PROFILE_H
#define _PROFILE_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>
#include <vector>
#include <sys/time.h>
#include <logger.h>

#define	TIME_BUCKETS	20
#define BUCKET_SIZE	5
class ProfileItem
{
	public:
		ProfileItem(const std::string& reference) : m_reference(reference)
			{ gettimeofday(&m_tvStart, NULL);
				auto timenow = chrono::system_clock::to_time_t(chrono::system_clock::now());
				m_ts = std::string(ctime(&timenow));
				m_ts.back() = '\0'; };
		~ProfileItem() {};
		void 	complete()
			{
				struct timeval tv;

				gettimeofday(&tv, NULL);
				m_duration = (tv.tv_sec - m_tvStart.tv_sec) * 1000 +
				(tv.tv_usec - m_tvStart.tv_usec) / 1000;
			};
		unsigned long getDuration() { return m_duration; };
		const std::string& getReference() const { return m_reference; };
		const std::string& getTs() const { return m_ts; };
	private:
		std::string		m_reference;
		struct timeval		m_tvStart;
		unsigned long		m_duration;
		std::string		m_ts;
};

class QueryProfile
{
	public:
		QueryProfile(int samples) : m_samples(samples) { time(&m_lastReport); };
		void	insert(ProfileItem *item)
			{
				int b = item->getDuration() / BUCKET_SIZE;
				if (b >= TIME_BUCKETS)
					b = TIME_BUCKETS - 1;
				m_buckets[b]++;
				if (m_items.size() == m_samples)
				{
					int minIndex = 0;
					unsigned long minDuration = m_items[0]->getDuration();
					for (int i = 1; i < m_items.size(); i++)
					{
						if (m_items[i]->getDuration() < minDuration)
						{
							minDuration = m_items[i]->getDuration();
							minIndex = i;
						}
					}
					if (item->getDuration() > minDuration)
					{
						delete m_items[minIndex];
						m_items[minIndex] = item;
					}
					else
					{
						delete item;
					}
				}
				else
				{
					m_items.push_back(item);
				}
				if (time(0) - m_lastReport > 600)
				{
					report();
				}
			};
	private:
		int				m_samples;
		std::vector<ProfileItem *>	m_items;
		time_t				m_lastReport;
		unsigned int			m_buckets[TIME_BUCKETS];
		void	report()
			{
				Logger *logger = Logger::getLogger();
				logger->info("Storage profile report");
				logger->info(" < %3d mS %d", BUCKET_SIZE, m_buckets[0]);
				for (int j = 1; j < TIME_BUCKETS - 1; j++)
				{
					logger->info("%3d-%3d mS %d",
						j * BUCKET_SIZE, (j + 1) * BUCKET_SIZE,
						m_buckets[j]);
				}
				logger->info(" > %3d mS %d", BUCKET_SIZE * TIME_BUCKETS, m_buckets[TIME_BUCKETS-1]);
				for (int i = 0; i < m_items.size(); i++)
				{
					logger->info("%ld mS, %s, %s\n",
						m_items[i]->getDuration(),
						m_items[i]->getTs().c_str(),
						m_items[i]->getReference().c_str());
				}
				time(&m_lastReport);
			};
};
#endif

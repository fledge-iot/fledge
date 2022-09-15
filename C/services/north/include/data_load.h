#ifndef _DATA_LOAD_H
#define _DATA_LOAD_H

#include <string>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <deque>
#include <storage_client.h>
#include <reading.h>
#include <filter_pipeline.h>
#include <service_handler.h>

#define DEFAULT_BLOCK_SIZE 100

/**
 * A class used in the North service to load data from the buffer
 *
 * This class is responsible for loading the reading from the 
 * storage service and buffering them ready for the egress thread
 * to process them.
 */
class DataLoad : public ServiceHandler {
	public:
		DataLoad(const std::string& name, long streamId,
			       	StorageClient *storage);
		virtual ~DataLoad();

		void			loadThread();
		bool			setDataSource(const std::string& source);
		void			triggerRead(unsigned int blockSize);
		void			updateLastSentId(unsigned long id);
		ReadingSet		*fetchReadings(bool wait);
		void			updateStatistics(uint32_t increment);
		static void		passToOnwardFilter(OUTPUT_HANDLE *outHandle,
						READINGSET* readings);
		static void		pipelineEnd(OUTPUT_HANDLE *outHandle,
						READINGSET* readings);
		void			shutdown();
		void			restart();
		bool			isRunning() { return !m_shutdown; };
		void			configChange(const std::string& category, const std::string& newConfig);
		void			configChildCreate(const std::string& , const std::string&, const std::string&){};
		void			configChildDelete(const std::string& , const std::string&){};
		unsigned long		getLastFetched() { return m_lastFetched; };
		void			setBlockSize(unsigned long blockSize)
					{
						m_blockSize = blockSize;
					};

	private:
		void			readBlock(unsigned int blockSize);
		unsigned int		waitForReadRequest();
		unsigned long		getLastSentId();
		int			createNewStream();
		ReadingSet		*fetchStatistics(unsigned int blockSize);
		ReadingSet		*fetchAudit(unsigned int blockSize);
		void			bufferReadings(ReadingSet *readings);
		bool			loadFilters(const std::string& category);
		void			updateStatistic(const std::string& key, const std::string& description, uint32_t increment);
	private:
		const std::string&	m_name;
		long			m_streamId;
		StorageClient		*m_storage;
		volatile bool		m_shutdown;
		std::thread		*m_thread;
		std::mutex		m_mutex;
		std::condition_variable m_cv;
		std::condition_variable m_fetchCV;
		unsigned int		m_readRequest;
		enum { SourceReadings, SourceStatistics, SourceAudit }
					m_dataSource;
		unsigned long		m_lastFetched;
		std::deque<ReadingSet *>
					m_queue;
		std::mutex		m_qMutex;
		FilterPipeline		*m_pipeline;
		std::mutex		m_pipelineMutex;
		unsigned long		m_blockSize;
};
#endif

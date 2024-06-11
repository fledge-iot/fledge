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
#include <perfmonitors.h>

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
		void			flushLastSentId();
		ReadingSet		*fetchReadings(bool wait);
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
		void			setStreamUpdate(unsigned long streamUpdate)
					{
						m_streamUpdate = streamUpdate;
						m_nextStreamUpdate = streamUpdate;
					};
		void			setPerfMonitor(PerformanceMonitor *perfMonitor) { m_perfMonitor = perfMonitor; };
		const std::string	&getName() { return m_name; };
		StorageClient		*getStorage() { return m_storage; }; 
		void			setPrefetchLimit(unsigned int limit)
					{
						m_prefetchLimit = limit;
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
		PerformanceMonitor	*m_perfMonitor;
		int			m_streamUpdate;
		unsigned long		m_streamSent;
		int			m_nextStreamUpdate;
		unsigned int		m_prefetchLimit;
		bool			m_flushRequired;
};
#endif

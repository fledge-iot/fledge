#ifndef _SENDING_PROCESS_H
#define _SENDING_PROCESS_H

/*
 * Fledge process class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <process.h>
#include <thread>
#include <north_plugin.h>
#include <reading.h>
#include <filter_plugin.h>
#include <north_filter_pipeline.h>
#include <asset_tracking.h>

// SendingProcess class
class SendingProcess : public FledgeProcess
{
	public:
		// Constructor:
		SendingProcess(int argc, char** argv);

		// Destructor
		~SendingProcess();

		void			run() const;
		void			stop();
		int			getStreamId() const { return m_stream_id; };
		bool			isRunning() const { if (m_dryRun) return false; return m_running; };
		void			stopRunning() { m_running = false; };
		void			setLastFetchId(unsigned long id) { m_last_fetch_id = id; };
		unsigned long		getLastFetchId() const { return m_last_fetch_id; };
		void			setLastSentId(unsigned long id) { m_last_sent_id = id; };
		unsigned long		getLastSentId() const { return m_last_sent_id; };

		unsigned long		getSentReadings() const { return m_tot_sent; };
		bool			updateSentReadings(unsigned long num) {
						m_tot_sent += num;
						return m_tot_sent;
		};
		void			resetSentReadings() { m_tot_sent = 0; };
		void			updateDatabaseCounters();
		bool			getLastSentReadingId();
		bool			createStream(int);
		int			createNewStream();
		unsigned int		getDuration() const { return m_duration; };
		unsigned int		getSleepTime() const { return m_sleep; };
		bool			getUpdateDb() const { return m_update_db; };
		bool			setUpdateDb(bool val) {
						    m_update_db = val;
						    return m_update_db;
		};
		unsigned long		getReadBlockSize() const { return m_block_size; };
		const std::string& 	getDataSourceType() const { return m_data_source_t; };
		const std::string& 	getPluginName() const { return m_plugin_name; };
		void			setLoadBufferIndex(unsigned long loadBufferIdx);
		unsigned long		getLoadBufferIndex() const;
		const unsigned long*	getLoadBufferIndexPtr() const;

    		unsigned long		getMemoryBufferSize() const { return m_memory_buffer_size; };
    		void 			createConfigCategories(DefaultConfigCategory configCategory,
    							       std::string parent_name,
    							       std::string current_name,
    							       std::string current_description);

    // Public static methods
	public:
		static void		setLoadBufferData(unsigned long index,
							  ReadingSet* readings);
		static std::vector<ReadingSet *>*
					getDataBuffers() { return m_buffer_ptr; };
		static void		useFilteredData(OUTPUT_HANDLE *outHandle,
							READINGSET* readings);
		static void		passToOnwardFilter(OUTPUT_HANDLE *outHandle,
							   READINGSET* readings);

	private:
		std::string             retrieveTableInformationName(const char* dataSource);
		void                    updateStreamLastSentId(long lastSentId);
		void			setDuration(unsigned int val) { m_duration = val; };
		void			setSleepTime(unsigned long val) { m_sleep = val; };
		void			setReadBlockSize(unsigned long size) { m_block_size = size; };
		bool			loadPlugin(const std::string& pluginName);
		ConfigCategory		fetchConfiguration(const std::string& defCfg,
							   const std::string& pluginName);
		bool			loadFilters(const std::string& pluginName);
		void 			updateStatistics(std::string& stat_key,
							 const std::string& stat_description);

		// Make private the copy constructor and operator=
		SendingProcess(const SendingProcess &);
                SendingProcess&		operator=(SendingProcess const &);

	public:
		std::vector<ReadingSet *>	m_buffer;
		std::thread*			m_thread_load;
		std::thread*			m_thread_send;
		NorthPlugin*			m_plugin;
		std::vector<unsigned long>	m_last_read_id;
		NorthFilterPipeline*		filterPipeline;

	private:
		bool				m_running;
		int 				m_stream_id;
		unsigned long			m_last_sent_id;
    		unsigned long			m_last_fetch_id;
		unsigned long			m_tot_sent;
		unsigned int			m_duration;
		unsigned long			m_sleep;
		unsigned long			m_block_size;
		bool				m_update_db;
    		std::string			m_plugin_name;
                Logger*			        m_logger;
		std::string			m_data_source_t;
		unsigned long			m_load_buffer_index;
    		unsigned long			m_memory_buffer_size = 1;
		
		// static pointer for data buffer access
		static std::vector<ReadingSet *>*
						m_buffer_ptr;
		AssetTracker			*m_assetTracker;
};

#endif

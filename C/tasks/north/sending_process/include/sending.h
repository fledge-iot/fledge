#ifndef _SENDING_PROCESS_H
#define _SENDING_PROCESS_H

/*
 * FogLAMP process class
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

// Buffer max elements
#define DATA_BUFFER_ELMS 10

// SendingProcess class
class SendingProcess : public FogLampProcess
{
	public:
		// Constructor:
		SendingProcess(int argc, char** argv);

		// Destructor
		~SendingProcess();

		void			run() const;
		void			stop();
		int			getStreamId() const { return m_stream_id; };
		bool			isRunning() const { return m_running; };
		void			stopRunning() { m_running = false; };
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

	private:
		void			setDuration(unsigned int val) { m_duration = val; };
		void			setSleepTime(unsigned long val) { m_sleep = val; };
		void			setReadBlockSize(unsigned long size) { m_block_size = size; };
		bool			loadPlugin(const std::string& pluginName);
		const std::map<std::string, std::string>& fetchConfiguration(const std::string& defCfg,
									     const std::string& plugin_name);
		// Make private the copy constructor and operator=
		SendingProcess(const SendingProcess &);
                SendingProcess&		operator=(SendingProcess const &);

	public:
		std::vector<ReadingSet *>	m_buffer;
		std::thread*			m_thread_load;
		std::thread*			m_thread_send;
		NorthPlugin*			m_plugin;

	private:
		bool				m_running;
		int 				m_stream_id;
		unsigned long			m_last_sent_id;
		unsigned long			m_tot_sent;
		unsigned int			m_duration;
		unsigned long			m_sleep;
		unsigned long			m_block_size;
		bool				m_update_db;
    		std::string			m_plugin_name;
                Logger*			        m_logger;
		std::string			m_data_source_t;
};

#endif

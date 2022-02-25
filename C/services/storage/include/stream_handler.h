#ifndef _STREAM_HANDLER_H
#define _STREAM_HANDLER_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2019 Dianomic Systems Inc.
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <thread>
#include <mutex>
#include <condition_variable>
#include <vector>
#include <map>
#include <sys/epoll.h>
#include <reading_stream.h>

#define MAX_EVENTS	  40	// Number of epoll events in one epoll_wait call
#define RDS_BLOCK	 10000	// Number of readings to insert in each call to the storage plugin
#define BLOCK_POOL_SIZES 512	// Increments of block sizes in a block pool

class StorageApi;

class StreamHandler {
	public:
		StreamHandler(StorageApi *);
		~StreamHandler();
		void			handler();
		uint32_t		createStream(uint32_t *token);
	private:
		class Stream {
			public:
				Stream();
				~Stream();
				uint32_t	create(int epollfd, uint32_t *token);
				void		handleEvent(int epollfd, StorageApi *api, uint32_t events);
			private:
				/**
				 * A simple memory pool we use to store the messages we receive.
				 * We use this rather than malloc because it let's us avoid the overhead of
				 * the more complex heap mamagement and also because it means we avoid
				 * taking out a process wide mutex.
				 */
				class MemoryPool {
						public:
							MemoryPool(size_t blkIncr) : m_blkIncr(blkIncr) {};
							~MemoryPool();
							void		*allocate(size_t size);
							void		release(void *handle);
						private:
							size_t		rndSize(size_t size)
									{ 
										return m_blkIncr * ((size + m_blkIncr - 1)
											       	/ m_blkIncr);
									};
							void		createPool(size_t size);
							void		growPool(std::vector<void *>*, size_t);
							size_t		m_blkIncr;
							std::map<size_t, std::vector<void *>* >
									m_pool;
					};
					void		setNonBlocking(int fd);
					unsigned int	available(int fd);
					void		queueInsert(StorageApi *api, unsigned int nReadings, bool commit);
					void		dump(int n);
					enum { Closed, Listen, AwaitingToken, Connected }
				       			m_status;
					int		m_socket;
					uint16_t	m_port;
					uint32_t	m_token;
					uint32_t	m_blockNo;
					enum { BlkHdr, RdHdr, RdBody }
				       			m_protocolState;
					uint32_t	m_readingNo;
					uint32_t	m_blockSize;
					size_t		m_readingSize;
					struct epoll_event
							m_event;
					ReadingStream	*m_readings[RDS_BLOCK+1];
					ReadingStream	*m_currentReading;
					MemoryPool	*m_blockPool;
					std::string	m_lastAsset;
					bool		m_sameAsset;
		};
		StorageApi		*m_api;
		std::thread		m_handlerThread;
		int			m_tokens;
		std::condition_variable	m_streamsCV;
		std::mutex		m_streamsMutex;
		std::vector<Stream *>	m_streams;
		bool			m_running;
		int			m_pollfd;
};
#endif

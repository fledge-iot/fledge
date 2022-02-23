/*
 * Fledge storage service.
 *
 * Copyright (c) 2019 Dianomic Systems Inc
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <stream_handler.h>
#include <storage_api.h>
#include <storage_api.h>
#include <reading_stream.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <sys/epoll.h>
#include <sys/ioctl.h>
#include <chrono>
#include <unistd.h>
#include <errno.h>


using namespace std;

/**
 * C wrapper for the handler thread we use to handle the polling of
 * the stream ingestion protocol.
 *
 * @param handler	The SgtreamHanler instance that started this thread
 */
static void threadWrapper(void *handler)
{
	((StreamHandler *)handler)->handler();
}

/**
 * Constructor for the StreamHandler class
 */
StreamHandler::StreamHandler(StorageApi *api) : m_api(api), m_running(true)
{
	m_pollfd = epoll_create(1);
	m_handlerThread = thread(threadWrapper, this);
}


/**
 * Destructor for the StreamHandler. Close down the epoll
 * system and wait for the handler thread to terminate.
 */
StreamHandler::~StreamHandler()
{
	m_running = false;
	close(m_pollfd);
	m_handlerThread.join();
}

/**
 * The handler method for the stream handler. This is run in its own thread
 * and is responsible for using epoll to gather events on the descriptors and
 * to dispatch them to the individual streams
 */
void StreamHandler::handler()
{
	struct epoll_event events[MAX_EVENTS];
	while (m_running)
	{
		std::unique_lock<std::mutex> lock(m_streamsMutex);
		if (m_streams.size() == 0)
		{
			Logger::getLogger()->debug("Waiting for first stream to be created");
			m_streamsCV.wait_for(lock, chrono::milliseconds(500));
		}
		else
		{
			int nfds = epoll_wait(m_pollfd, events, MAX_EVENTS, 1);
			for (int i = 0; i < nfds; i++)
			{
				Stream *stream = (Stream *)events[i].data.ptr;
				stream->handleEvent(m_pollfd, m_api, events[i].events);
			}
		}
	}
}

/**
 * Create a new stream and add it to the epoll mechanism for the stream handler
 *
 * @param token		The single use connection token the client should send
 * @param The port on which this stream is listening
 */
uint32_t StreamHandler::createStream(uint32_t *token)
{
	Stream *stream = new Stream();
	uint32_t port = stream->create(m_pollfd, token);
	{
		std::unique_lock<std::mutex> lock(m_streamsMutex);
		m_streams.push_back(stream);
	}

	m_streamsCV.notify_all();

	return port;
}

/**
 * Create a stream object to deal with the stream protocol
 */
StreamHandler::Stream::Stream() : m_status(Closed)
{
}

/**
 * Destroy a stream
 */
StreamHandler::Stream::~Stream() 
{
	delete m_blockPool;
}

/**
 * Create a new stream object. Add that stream to the epoll structure.
 * A listener socket is created and the port sent back to the caller. The client
 * will connect to this port and then send the token to verify they are the 
 * service that requested the stream to be connected.
 *
 * @param epollfd	The epoll descriptor
 * @param token		The single use token the client will send in the connect request
 */
uint32_t StreamHandler::Stream::create(int epollfd, uint32_t *token)
{
struct sockaddr_in	address;

	if ((m_blockPool = new MemoryPool(BLOCK_POOL_SIZES)) == NULL)
	{
		Logger::getLogger()->error("Failed to create memory block pool");
		return 0;
	}

	if ((m_socket = socket(AF_INET, SOCK_STREAM, 0)) < 0)
	{
		Logger::getLogger()->error("Failed to create socket: %s", strerror(errno));
		return 0;
	}
	address.sin_family = AF_INET;
	address.sin_addr.s_addr = INADDR_ANY;
	address.sin_port = 0;

	if (bind(m_socket, (struct sockaddr *)&address, sizeof(address)) < 0)
	{
		Logger::getLogger()->error("Failed to bind socket: %s", strerror(errno));
		return 0;
	}
	socklen_t len = sizeof(address);
	if (getsockname(m_socket, (struct sockaddr *)&address, &len) == -1)
		Logger::getLogger()->error("Failed to get socket name, %s", strerror(errno));
	m_port = ntohs(address.sin_port);
	Logger::getLogger()->info("Stream port bound to %d", m_port);
	setNonBlocking(m_socket);

	if (listen(m_socket, 3) < 0)
	{
		Logger::getLogger()->error("Failed to listen: %s", strerror(errno));
		return 0;
    	}
	m_status = Listen;

	srand(m_port + (unsigned int)time(0));
	m_token = (uint32_t)random() & 0xffffffff;
	*token = m_token;

	// Add to epoll set
	m_event.data.ptr = this;
	m_event.events = EPOLLIN | EPOLLRDHUP;
	if (epoll_ctl(epollfd, EPOLL_CTL_ADD, m_socket, &m_event) < 0)
	{
		Logger::getLogger()->error("Failed to add listening port %d to epoll fileset, %s", m_port, strerror(errno));
	}

	return m_port;
}

/**
 * Set the file descriptor to be non blocking
 *
 * @param fd	The file descripter to set non-blocking
 */
void StreamHandler::Stream::setNonBlocking(int fd)
{
	int flags;
	flags = fcntl(fd, F_GETFL, 0);
	flags |= O_NONBLOCK;
	fcntl(fd, F_SETFL, flags);
}

/**
 * Handle an epoll event. The precise handling will depend
 * on the state of the stream.
 *
 * TODO Improve memory handling, use seperate threads for inserts, send acknowledgements
 *
 * @param epollfd	The epoll file descriptor
 */
void StreamHandler::Stream::handleEvent(int epollfd, StorageApi *api, uint32_t events)
{
ssize_t n;

	if (events & EPOLLRDHUP)
	{
		// TODO mark this stream for destruction
		epoll_ctl(epollfd, EPOLL_CTL_DEL, m_socket, &m_event);
		close(m_socket);
		Logger::getLogger()->warn("Closing stream...");
	}
	if (events & EPOLLIN)
	{
		if (m_status == Listen)
		{
			int conn_sock;
			struct sockaddr	addr;
			socklen_t	addrlen = sizeof(addr);
			if ((conn_sock = accept(m_socket,
						  (struct sockaddr *)&addr, &addrlen)) == -1)
			{
				Logger::getLogger()->info("Accept failed for streaming socket: %s", strerror(errno));
				return;
			}
			epoll_ctl(epollfd, EPOLL_CTL_DEL, m_socket, &m_event);
			close(m_socket);
			Logger::getLogger()->info("Stream connection established");
			m_socket = conn_sock;
			m_status = AwaitingToken;
			setNonBlocking(m_socket);
			m_event.events = EPOLLIN | EPOLLRDHUP;
			m_event.data.ptr = this;
			epoll_ctl(epollfd, EPOLL_CTL_ADD, m_socket, &m_event);
		}
		else if (m_status == AwaitingToken)
		{
			RDSConnectHeader	hdr;
			if (available(m_socket) < sizeof(hdr))
			{
				return;
			}
			if ((n = read(m_socket, &hdr, sizeof(hdr))) != (int)sizeof(hdr))
				Logger::getLogger()->warn("Token exchange: Short read of %d bytes: %s", n, strerror(errno));
			if (hdr.magic == RDS_CONNECTION_MAGIC && hdr.token == m_token)
			{
				m_status = Connected;
				m_blockNo = 0;
				m_readingNo = 0;
				m_protocolState = BlkHdr;
				Logger::getLogger()->info("Token for streaming socket exchanged");
			}
			else
			{
				Logger::getLogger()->warn("Incorrect token for streaming socket");
				close(m_socket);
			}
		}
		else if (m_status == Connected)
		{
			while (1)
			{
				Logger::getLogger()->debug("Connected in protocol state %d, readingNo %d", m_protocolState, m_readingNo);
				if (m_protocolState == BlkHdr)
				{
					RDSBlockHeader blkHdr;
					if (available(m_socket) < sizeof(blkHdr))
					{
						Logger::getLogger()->debug("Not enough bytes for block header");
						return;
					}
					if ((n = read(m_socket, &blkHdr, sizeof(blkHdr))) != (int)sizeof(blkHdr))
					{
						if (errno == EAGAIN)
							return;
						Logger::getLogger()->warn("Block Header: Short read of %d bytes: %s", n, strerror(errno));
						return;
					}
					if (blkHdr.magic != RDS_BLOCK_MAGIC)
					{
						Logger::getLogger()->error("Expected block header %d, but incorrect header found 0x%x", m_blockNo, blkHdr.magic);
						Logger::getLogger()->error("Previous block size was %d", m_blockSize);
						dump(10);
						close(m_socket);
						return;
					}
					if (blkHdr.blockNumber != m_blockNo)
					{
					}
					m_blockNo++;
					m_blockSize = blkHdr.count;
					m_protocolState = RdHdr;
					m_readingNo = 0;
					Logger::getLogger()->debug("New block %d of %d readings", blkHdr.blockNumber, blkHdr.count);
				}
				else if (m_protocolState == RdHdr)
				{
					RDSReadingHeader rdhdr;
					if (available(m_socket) < sizeof(rdhdr))
					{
						Logger::getLogger()->debug("Not enough bytes for reading header");
						return;
					}
					if (read(m_socket, &rdhdr, sizeof(rdhdr)) < (int)sizeof(rdhdr))
					{
						if (errno == EAGAIN)
							return;
						Logger::getLogger()->warn("Not enough bytes for reading header");
						return;
					}
					if (rdhdr.magic != RDS_READING_MAGIC)
					{
						Logger::getLogger()->error("Expected reading header %d of %d in block %d, but incorrect header found 0x%x", m_readingNo, m_blockSize, m_blockNo, rdhdr.magic);
						dump(10);
						close(m_socket);
						return;
					}
					Logger::getLogger()->debug("Reading Header: assetCodeLngth %d, payloadLength %d", rdhdr.assetLength, rdhdr.payloadLength);
					m_readingSize = sizeof(struct timeval) + rdhdr.assetLength + rdhdr.payloadLength;
					uint32_t extra = 0;
					if (rdhdr.assetLength)
					{
						m_sameAsset = false;
						extra = 0;
					}
					else
					{
						m_sameAsset = true;
						extra = m_lastAsset.length() + 1;
						rdhdr.assetLength = extra;
					}
					extra  += 2 * sizeof(uint32_t);
					m_currentReading = (ReadingStream *)m_blockPool->allocate(m_readingSize + extra);
					m_readings[m_readingNo % RDS_BLOCK] = m_currentReading;
					m_currentReading->assetCodeLength = rdhdr.assetLength;
					m_currentReading->payloadLength = rdhdr.payloadLength;
					m_protocolState = RdBody;
				}
				else if (m_protocolState == RdBody)
				{
					if (available(m_socket) < m_readingSize)
					{
						Logger::getLogger()->debug("Not enough bytes for reading %d", m_readingSize);
						return;
					}
					if (m_sameAsset)
					{
						if ((n = read(m_socket, &m_currentReading->userTs, sizeof(struct timeval))) != (int)sizeof(struct timeval))
							Logger::getLogger()->warn("Short read of %d bytes for timestamp: %s", n, strerror(errno));
						size_t plen = m_readingSize - sizeof(struct timeval);
						uint32_t assetLen = m_currentReading->assetCodeLength;
						if ((n = read(m_socket, &m_currentReading->assetCode[assetLen], plen)) < (int)plen)
							Logger::getLogger()->warn("Short read of %d bytes for payload: %s", n, strerror(errno));
						memcpy(&m_currentReading->assetCode[0], m_lastAsset.c_str(), assetLen);
					}
					else
					{
						if ((n = read(m_socket, &m_currentReading->userTs, m_readingSize)) != (int)m_readingSize)
							Logger::getLogger()->warn("Short read of %d bytes for reading: %s", n, strerror(errno));
						m_lastAsset = m_currentReading->assetCode;
					}
					m_readingNo++;
					if ((m_readingNo % RDS_BLOCK) == 0)
					{
						queueInsert(api, RDS_BLOCK, false);
						for (int i = 0; i < RDS_BLOCK; i++)
							m_blockPool->release(m_readings[i]);
					}
					else if (m_readingNo == m_blockSize)
					{
						// We have completed the block, insert readings and wait
						// for a block header
						queueInsert(api, m_readingNo % RDS_BLOCK, true);
						for (uint32_t i = 0; i < m_readingNo % RDS_BLOCK; i++)
							m_blockPool->release(m_readings[i]);
					}
					if (m_readingNo >= m_blockSize)
					{
						m_protocolState = BlkHdr;
					}
					else
					{
						m_protocolState = RdHdr;
					}
				}
			}
		}
	}
}

/**
 * Queue a block of readings to be inserted into the database. The readings
 * are available via the m_readings array.
 *
 * @param nReadings	The number of readings to insert
 * @param commit	Perform commit at end of this block
 */
void StreamHandler::Stream::queueInsert(StorageApi *api, unsigned int nReadings, bool commit)
{
	m_readings[nReadings] = NULL;
	api->readingStream(m_readings, commit);
}

/**
 * Return the number of bytes available to read on the
 * given file descriptor
 *
 * @param fd	The file descriptor to check
 */
unsigned int  StreamHandler::Stream::available(int fd)
{
unsigned int	avail;

	if (ioctl(fd, FIONREAD, &avail) < 0)
	{
		Logger::getLogger()->warn("FIONREAD failed: %s", strerror(errno));
		return 0;
	}
	return avail;
}

/**
 * Block memory pool destructor. Return any memory from the memory pools
 * to the system.
 */
StreamHandler::Stream::MemoryPool::~MemoryPool()
{
	for (auto it = m_pool.begin(); it != m_pool.end(); it++)
        {
                while (! it->second->empty())
                {
			void *mem = it->second->back();
			it->second->pop_back();
                        free(&((size_t *)mem)[-1]);
                }
		delete it->second;
        }
}

/**
 * Allocate a buffer from the block pool
 *
 * @param size	Minimum size of block to allocate
 */
void *StreamHandler::Stream::MemoryPool::allocate(size_t size)
{
	size = rndSize(size);
	auto blkpool = m_pool.find(size);
	if (blkpool == m_pool.end())
	{
		Logger::getLogger()->info("No block pool for %d bytes, creating", size);
		// Create a new memory pool
		createPool(size);
		blkpool = m_pool.find(size);
	}
	if (blkpool->second->empty())
	{
		Logger::getLogger()->warn("Extending block pool for %d bytes", size);
		growPool(blkpool->second, size);
	}
	void *memory = blkpool->second->back();
	blkpool->second->pop_back();

	return memory;
}

/**
 * Release memory back to the memory pool
 *
 * @param memory	The memory to release
 */
void StreamHandler::Stream::MemoryPool::release(void *memory)
{
	size_t poolSize = ((size_t *)memory)[-1];
	auto blkpool = m_pool.find(poolSize);
	if (blkpool == m_pool.end())
	{
		Logger::getLogger()->fatal("Returning memory to a block pool (%d) that does not exist", poolSize);
		throw runtime_error("Invalid block pool");
	}
	blkpool->second->push_back(memory);
}

/**
 * Allocate a new memory block pool
 *
 * @param size	Size of the memory blocks in the pool
 */
void StreamHandler::Stream::MemoryPool::createPool(size_t size)
{
	size_t realSize = size + sizeof(size_t);
	vector<void *> *blocks = new vector<void *>;
	for (int i = 0; i < RDS_BLOCK; i++)
	{
		size_t *mem = (size_t *)malloc(realSize);
		blocks->push_back(&mem[1]);
		mem[0] = size;
	}
	m_pool.insert(pair<int, vector<void *>* >(size, blocks));
}

/**
 * Grow the memory pool for this size block
 *
 * @param pool		The memory pool
 * @param size		The size of the blocks in the memory pool
 */
void StreamHandler::Stream::MemoryPool::growPool(vector<void *> *pool, size_t size)
{
	size_t realSize = size + sizeof(size_t);
	for (int i = 0; i < RDS_BLOCK; i++)
	{
		size_t *mem = (size_t *)malloc(realSize);
		pool->push_back(&mem[1]);
		mem[0] = size;
	}
}

/**
 * Diagnostic routine to display stream content.
 *
 * @param n Number of lines to display
 */
void StreamHandler::Stream::dump(int n)
{
	char buf[132];
	char data[10];
	while (n--)
	{
		buf[0] = 0;
		int r = read(m_socket, data, 10);
		for (int i = 0; i < r; i++)
		{
			char one[8];
			snprintf(one, sizeof(one), "0x%02x ", data[i]);
			strcat(buf, one);
		}
		Logger::getLogger()->error(buf);
	}
}

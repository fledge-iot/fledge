#ifndef _READING_STREAM_H
#define _READING_STREAM_H
/*
 * Fledge storage reading stream protocol definitions.
 *
 * Copyright (c) 2019 Dianomic Systems Inc.
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#define RDS_CONNECTION_MAGIC	0x344f4e4e
#define	RDS_BLOCK_MAGIC		0x5244424b
#define	RDS_READING_MAGIC	0x52444947
#define RDS_ACK_MAGIC		0x4241434b
#define RDS_NACK_MAGIC		0x4e41434b

typedef struct {
	uint32_t	magic;
	uint32_t	token;
} RDSConnectHeader;

typedef struct {
	uint32_t	magic;
	uint32_t	blockNumber;
	uint32_t	count;
} RDSBlockHeader;

typedef struct {
	uint32_t	magic;
	uint32_t	readingNo;
	uint32_t	assetLength;
	uint32_t	payloadLength;
} RDSReadingHeader;

typedef struct {
	uint32_t	magic;
	uint32_t	block;
} RDSAcknowledge;

typedef struct {
	uint32_t	assetCodeLength;
	uint32_t 	payloadLength;
	struct timeval	userTs;
	char		assetCode[1];
} ReadingStream;

#endif


/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <sql_buffer.h>
#include <string.h>

using namespace std;
/**
 * Buffer class designed to hold SQL statement that can
 * as required but have minimal copy semantics.
 */

/**
 * SQLBuffer constructor
 */
SQLBuffer::SQLBuffer()
{
        buffers.push_front(new SQLBuffer::Buffer());
}

/**
 * SQLBuffer destructor
 */
SQLBuffer::~SQLBuffer()
{
	for (list<SQLBuffer::Buffer *>::iterator it = buffers.begin(); it != buffers.end(); ++it)
	{
		delete *it;
	}
}

/**
 * Append a character to a buffer
 */
void SQLBuffer::append(const char data)
{
SQLBuffer::Buffer *buffer = buffers.back();

        if (buffer->offset == buffer->length)
        {
		buffer = new SQLBuffer::Buffer();
		buffers.push_back(buffer);
	}
	buffer->data[buffer->offset] = data;
	buffer->data[buffer->offset + 1] = 0;
	buffer->offset++;
}

/**
 * Append a character string to a buffer
 */
void SQLBuffer::append(const char *data)
{
unsigned int len = strlen(data);
SQLBuffer::Buffer *buffer = buffers.back();

        if (buffer->offset + len >= buffer->length)
        {
		if (len > BUFFER_CHUNK)
		{
			buffer = new SQLBuffer::Buffer(len + BUFFER_CHUNK);
		}
		else
		{
			buffer = new SQLBuffer::Buffer();
		}
		buffers.push_back(buffer);
	}
	memcpy(&buffer->data[buffer->offset], data, len);
	buffer->offset += len;
	buffer->data[buffer->offset] = 0;
}

/**
 * Append an integer to a buffer
 */
void SQLBuffer::append(const int value)
{
char	tmpbuf[80];
unsigned int len;
SQLBuffer::Buffer *buffer = buffers.back();

	len = (unsigned int)snprintf(tmpbuf, 80, "%d", value);
        if (buffer->offset + len >= buffer->length)
        {
		buffer = new SQLBuffer::Buffer();
		buffers.push_back(buffer);
	}
	memcpy(&buffer->data[buffer->offset], tmpbuf, len);
	buffer->offset += len;
	buffer->data[buffer->offset] = 0;
}

/**
 * Append a long to a buffer
 */
void SQLBuffer::append(const long value)
{
char	tmpbuf[80];
unsigned int len;
SQLBuffer::Buffer *buffer = buffers.back();

	len = (unsigned int)snprintf(tmpbuf, 80, "%ld", value);
        if (buffer->offset + len >= buffer->length)
        {
		buffer = new SQLBuffer::Buffer();
		buffers.push_back(buffer);
	}
	memcpy(&buffer->data[buffer->offset], tmpbuf, len);
	buffer->offset += len;
	buffer->data[buffer->offset] = 0;
}

/**
 * Append an unsigned integer to a buffer
 */
void SQLBuffer::append(const unsigned int value)
{
char	tmpbuf[80];
unsigned int len;
SQLBuffer::Buffer *buffer = buffers.back();

	len = (unsigned int)snprintf(tmpbuf, 80, "%u", value);
        if (buffer->offset + len >= buffer->length)
        {
		buffer = new SQLBuffer::Buffer();
		buffers.push_back(buffer);
	}
	memcpy(&buffer->data[buffer->offset], tmpbuf, len);
	buffer->offset += len;
	buffer->data[buffer->offset] = 0;
}

/**
 * Append an unsigned long to a buffer
 */
void SQLBuffer::append(const unsigned long value)
{
char	tmpbuf[80];
unsigned int len;
SQLBuffer::Buffer *buffer = buffers.back();

	len = (unsigned int)snprintf(tmpbuf, 80, "%lu", value);
        if (buffer->offset + len >= buffer->length)
        {
		buffer = new SQLBuffer::Buffer();
		buffers.push_back(buffer);
	}
	memcpy(&buffer->data[buffer->offset], tmpbuf, len);
	buffer->offset += len;
	buffer->data[buffer->offset] = 0;
}

/**
 * Append a double to a buffer
 */
void SQLBuffer::append(const double value)
{
char	tmpbuf[80];
unsigned int len;
SQLBuffer::Buffer *buffer = buffers.back();

	len = (unsigned int)snprintf(tmpbuf, 80, "%f", value);
        if (buffer->offset + len >= buffer->length)
        {
		buffer = new SQLBuffer::Buffer();
		buffers.push_back(buffer);
	}
	memcpy(&buffer->data[buffer->offset], tmpbuf, len);
	buffer->offset += len;
	buffer->data[buffer->offset] = 0;
}

/**
 * Append a string to a buffer
 */
void SQLBuffer::append(const string& str)
{
const char	*cstr = str.c_str();
unsigned int len = strlen(cstr);
SQLBuffer::Buffer *buffer = buffers.back();

        if (buffer->offset + len >= buffer->length)
        {
		if (len > BUFFER_CHUNK)
		{
			buffer = new SQLBuffer::Buffer(len + BUFFER_CHUNK);
		}
		else
		{
			buffer = new SQLBuffer::Buffer();
		}
		buffers.push_back(buffer);
	}
	memcpy(&buffer->data[buffer->offset], cstr, len);
	buffer->offset += len;
	buffer->data[buffer->offset] = 0;
}

/**
 * Create a coalesced buffer from the buffer chain
 */
const char *SQLBuffer::coalesce()
{
unsigned int length = 0, offset = 0;
char	     *buffer = 0;

	if (buffers.size() == 1)
	{
		return buffers.back()->detach();
	}
	for (list<SQLBuffer::Buffer *>::iterator it = buffers.begin(); it != buffers.end(); ++it)
	{
		length += (*it)->offset;
	}
	buffer = new char[length+1];
	for (list<SQLBuffer::Buffer *>::iterator it = buffers.begin(); it != buffers.end(); ++it)
	{
		memcpy(&buffer[offset], (*it)->data, (*it)->offset);
		offset += (*it)->offset;
	}
	buffer[offset] = 0;
	return buffer;
}

/**
 * Construct a buffer
 */
SQLBuffer::Buffer::Buffer() : offset(0), length(BUFFER_CHUNK), attached(true)
{
	data = new char[BUFFER_CHUNK+1];
	data[0] = 0;
}

/**
 * Construct a large buffer
 */
SQLBuffer::Buffer::Buffer(unsigned int size) : offset(0), length(size), attached(true)
{
	data = new char[size+1];
	data[0] = 0;
}

/**
 * Buffer destructor
 */
SQLBuffer::Buffer::~Buffer()
{
	if (attached)
	{
		delete data;
		data = 0;
	}
}

char *SQLBuffer::Buffer::detach()
{
char *rval = data;

	attached = false;
	length = 0;
	data = 0;
	return rval;
}

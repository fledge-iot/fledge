/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <sql_buffer.h>
#include <string.h>
#include <string_utils.h>

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
 * Clear all the buffers from the SQLBuffer and allow it to be reused
 */
void SQLBuffer::clear()
{
	for (list<SQLBuffer::Buffer *>::iterator it = buffers.begin(); it != buffers.end(); ++it)
	{
		delete *it;
	}
	buffers.clear();
        buffers.push_front(new SQLBuffer::Buffer());
}

/**
 * Append a character to a buffer
 *
 * @param data	The character to append to the buffer
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
 *
 * @para data	The string to append to the buffer
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
 *
 * @param value	The value to append to the buffer
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
 *
 * @param value	The long value to append to the buffer
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
 *
 * @param value	The unsigned long value to append to the buffer
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
 *
 * @param value	The value to append to the buffer
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
 *
 * @param value	The double value to append to the buffer
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
 *
 * @param str	The string to be appended to the buffer
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
 * Quote and append a string to a buffer
 *
 * @param str	The string to quote and append to the buffer
 */
void SQLBuffer::quote(const string& str)
{
string esc = str;
StringEscapeQuotes(esc);
const char	*cstr = esc.c_str();
unsigned int len = strlen(cstr) + 2;
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
	buffer->data[buffer->offset] = '"';
	memcpy(&buffer->data[buffer->offset + 1], cstr, len - 2);
	buffer->data[buffer->offset + len - 1] = '"';
	buffer->offset += len;
	buffer->data[buffer->offset] = 0;
}

/**
 * Create a coalesced buffer from the buffer chain
 *
 * The buffer returned has been created usign the new[] operator and must be
 * deleted by the caller.
 * @return char* The SQL statement in a single buffer
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
 * Construct a buffer with a standard size initial buffer.
 */
SQLBuffer::Buffer::Buffer() : offset(0), length(BUFFER_CHUNK), attached(true)
{
	data = new char[BUFFER_CHUNK+1];
	data[0] = 0;
}

/**
 * Construct a large buffer, passign the size of buffer required. THis is useful
 * if you know your buffer requirements are large and you wish to reduce the amount
 * of allocation required.
 *
 * @param size	The size of the initial buffer to allocate.
 */
SQLBuffer::Buffer::Buffer(unsigned int size) : offset(0), length(size), attached(true)
{
	data = new char[size+1];
	data[0] = 0;
}

/**
 * Buffer destructor, the buffer itself is also deleted by this
 * call and any reference to it must no longer be used.
 */
SQLBuffer::Buffer::~Buffer()
{
	if (attached)
	{
		delete[] data;
		data = 0;
	}
}

/**
 * Detach the buffer from the SQLBuffer. The reference to the buffer
 * is removed from the SQLBuffer but the buffer itself is not deleted.
 * This allows the buffer ownership to be taken by external code
 * whilst allowing the SQLBuffer to allocate a new buffer.
 */
char *SQLBuffer::Buffer::detach()
{
char *rval = data;

	attached = false;
	length = 0;
	data = 0;
	return rval;
}

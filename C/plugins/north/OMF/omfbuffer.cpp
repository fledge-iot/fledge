/*
 * Fledge OMF north plugin buffer class
 *
 * Copyright (c) 2023 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <omfbuffer.h>
#include <string.h>
#include <string_utils.h>

using namespace std;
/**
 * Buffer class designed to hold OMF payloads that can
 * as required but have minimal copy semantics.
 */

/**
 * OMFBuffer constructor
 */
OMFBuffer::OMFBuffer()
{
        buffers.push_front(new OMFBuffer::Buffer());
}

/**
 * OMFBuffer destructor
 */
OMFBuffer::~OMFBuffer()
{
	for (list<OMFBuffer::Buffer *>::iterator it = buffers.begin(); it != buffers.end(); ++it)
	{
		delete *it;
	}
}

/**
 * Clear all the buffers from the OMFBuffer and allow it to be reused
 */
void OMFBuffer::clear()
{
	for (list<OMFBuffer::Buffer *>::iterator it = buffers.begin(); it != buffers.end(); ++it)
	{
		delete *it;
	}
	buffers.clear();
        buffers.push_front(new OMFBuffer::Buffer());
}

/**
 * Append a character to a buffer
 *
 * @param data	The character to append to the buffer
 */
void OMFBuffer::append(const char data)
{
OMFBuffer::Buffer *buffer = buffers.back();

        if (buffer->offset == buffer->length)
        {
		buffer = new OMFBuffer::Buffer();
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
void OMFBuffer::append(const char *data)
{
unsigned int len = strlen(data);
OMFBuffer::Buffer *buffer = buffers.back();

        if (buffer->offset + len >= buffer->length)
        {
		if (len > BUFFER_CHUNK)
		{
			buffer = new OMFBuffer::Buffer(len + BUFFER_CHUNK);
		}
		else
		{
			buffer = new OMFBuffer::Buffer();
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
void OMFBuffer::append(const int value)
{
char	tmpbuf[80];
unsigned int len;
OMFBuffer::Buffer *buffer = buffers.back();

	len = (unsigned int)snprintf(tmpbuf, 80, "%d", value);
        if (buffer->offset + len >= buffer->length)
        {
		buffer = new OMFBuffer::Buffer();
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
void OMFBuffer::append(const long value)
{
char	tmpbuf[80];
unsigned int len;
OMFBuffer::Buffer *buffer = buffers.back();

	len = (unsigned int)snprintf(tmpbuf, 80, "%ld", value);
        if (buffer->offset + len >= buffer->length)
        {
		buffer = new OMFBuffer::Buffer();
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
void OMFBuffer::append(const unsigned int value)
{
char	tmpbuf[80];
unsigned int len;
OMFBuffer::Buffer *buffer = buffers.back();

	len = (unsigned int)snprintf(tmpbuf, 80, "%u", value);
        if (buffer->offset + len >= buffer->length)
        {
		buffer = new OMFBuffer::Buffer();
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
void OMFBuffer::append(const unsigned long value)
{
char	tmpbuf[80];
unsigned int len;
OMFBuffer::Buffer *buffer = buffers.back();

	len = (unsigned int)snprintf(tmpbuf, 80, "%lu", value);
        if (buffer->offset + len >= buffer->length)
        {
		buffer = new OMFBuffer::Buffer();
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
void OMFBuffer::append(const double value)
{
char	tmpbuf[80];
unsigned int len;
OMFBuffer::Buffer *buffer = buffers.back();

	len = (unsigned int)snprintf(tmpbuf, 80, "%f", value);
        if (buffer->offset + len >= buffer->length)
        {
		buffer = new OMFBuffer::Buffer();
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
void OMFBuffer::append(const string& str)
{
const char	*cstr = str.c_str();
unsigned int len = strlen(cstr);
OMFBuffer::Buffer *buffer = buffers.back();

        if (buffer->offset + len >= buffer->length)
        {
		if (len > BUFFER_CHUNK)
		{
			buffer = new OMFBuffer::Buffer(len + BUFFER_CHUNK);
		}
		else
		{
			buffer = new OMFBuffer::Buffer();
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
void OMFBuffer::quote(const string& str)
{
string esc = str;
StringEscapeQuotes(esc);
const char	*cstr = esc.c_str();
unsigned int len = strlen(cstr) + 2;
OMFBuffer::Buffer *buffer = buffers.back();

        if (buffer->offset + len >= buffer->length)
        {
		if (len > BUFFER_CHUNK)
		{
			buffer = new OMFBuffer::Buffer(len + BUFFER_CHUNK);
		}
		else
		{
			buffer = new OMFBuffer::Buffer();
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
 * The buffer returned has been created using the new[] operator and must be
 * deleted by the caller.
 * @return char* The OMF payload in a single buffer
 */
const char *OMFBuffer::coalesce()
{
unsigned int length = 0, offset = 0;
char	     *buffer = 0;

	if (buffers.size() == 1)
	{
		return buffers.back()->detach();
	}
	for (list<OMFBuffer::Buffer *>::iterator it = buffers.begin(); it != buffers.end(); ++it)
	{
		length += (*it)->offset;
	}
	buffer = new char[length+1];
	for (list<OMFBuffer::Buffer *>::iterator it = buffers.begin(); it != buffers.end(); ++it)
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
OMFBuffer::Buffer::Buffer() : offset(0), length(BUFFER_CHUNK), attached(true)
{
	data = new char[BUFFER_CHUNK+1];
	data[0] = 0;
}

/**
 * Construct a large buffer, passing the size of buffer required. This is useful
 * if you know your buffer requirements are large and you wish to reduce the amount
 * of allocation required.
 *
 * @param size	The size of the initial buffer to allocate.
 */
OMFBuffer::Buffer::Buffer(unsigned int size) : offset(0), length(size), attached(true)
{
	data = new char[size+1];
	data[0] = 0;
}

/**
 * Buffer destructor, the buffer itself is also deleted by this
 * call and any reference to it must no longer be used.
 */
OMFBuffer::Buffer::~Buffer()
{
	if (attached)
	{
		delete[] data;
		data = 0;
	}
}

/**
 * Detach the buffer from the OMFBuffer. The reference to the buffer
 * is removed from the OMFBuffer but the buffer itself is not deleted.
 * This allows the buffer ownership to be taken by external code
 * whilst allowing the OMFBuffer to allocate a new buffer.
 */
char *OMFBuffer::Buffer::detach()
{
char *rval = data;

	attached = false;
	length = 0;
	data = 0;
	return rval;
}

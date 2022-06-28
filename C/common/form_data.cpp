/*
 * Fledge utilities functions for handling HTTP form data upload
 * with multipart data
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <form_data.h>
#include <errno.h>

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

// Class constructor with HTTP request object
FormData::FormData(shared_ptr<HttpServer::Request> request)
{
	// Boundary in the content has two additional '-' chars
	m_boundary = "--";

	// Get Content-Length from input header, if not found use request size
	auto header_it = request->header.find("Content-Length");
	if (header_it != request->header.end()) {
		m_size = std::stoull(header_it->second);
	}
	else
	{
		m_size = request->content.size();
	}

	// Get "Content-Type" which has content like:
	// Content-Type: multipart/form-data; boundary=------------------------XYZ
	header_it = request->header.find("Content-Type");
	if (header_it != request->header.end())
	{
		// Fetch multipart/form-data and boundary
		auto fileData = SimpleWeb::HttpHeader::FieldValue::SemicolonSeparatedAttributes::parse(header_it->second.c_str());
		for (auto it = fileData.begin();
			it != fileData.end();
			++it)
		{
			if (it->first == "boundary")
			{
				m_boundary += it->second.c_str();
			}
		}
	}

	// Get row data (const) from client request
	m_buffer = request->content.data();
}

/**
 * Skip a \r\n sequence
 *
 * @param b	Current buffer pointer
 * @return	Pointer after \r\n sequence
 */
uint8_t *FormData::skipSeparator(uint8_t *b)
{
	if ((b + 1) != NULL && (*b == CR && *(b + 1) == LF))
	{
		b += 2;
	}
	return b;
}

/**
 * Skip a double \r\n sequence
 *
 * @param b	Current buffer pointer
 * @return	Pointer after the double \r\n sequence
 */
uint8_t *FormData::skipDoubleSeparator(uint8_t *b)
{
	// Look for \r\n
	const uint8_t* ptr_end = m_buffer + m_size;
	for (; b < ptr_end; b++)
	{
		if ((b + 1) != NULL && (*b == CR && *(b + 1) == LF))
		{
			break;
		}
	}

	// Skip double \r\n sequence
	if (b && *b == CR && ((b + 1) && *(b + 1) == LF))
	{
		b += 2;
		if (b && *b == CR && ((b + 1) && *(b + 1) == LF))
		{
			b += 2;
		}
	}

	return b;
}

/**
 * Get end of content block, which can be binary data
 *
 * @param b	Current buffer pointer
 * @return	Pointer after the \r\n sequence + boundary
 */
uint8_t *FormData::getContentEnd(uint8_t *b)
{
	if (!b)
	{
		return NULL;
	}

	// Check content bytes
	// Look for boundary after \r\n as content end
	uint8_t *endOfContent = NULL;
	const uint8_t* ptr_end = m_buffer + m_size;
	for (; b < ptr_end; b++)
	{
		// Found \r\n
		if ((b + 2) != NULL && (*b == CR && *(b + 1) == LF))
		{
			endOfContent = (uint8_t *)strstr((char *)(b + 2), m_boundary.c_str());
			if (endOfContent)
			{
				// Found boundary: content ends here
				break;
			}
		}
	}

	// Boundary found
	if (endOfContent && (endOfContent - 2))
	{
		// Remove \r\n from end location
		endOfContent -= 2;
	}

	return endOfContent;
}

/**
 * Get given field name in the data buffer
 *
 * @param buffer	Current buffer pointer
 * @param field		The field name to find
 * @return		Pointer to filed value
 * 			if found or NULL otherwise
 */
uint8_t *FormData::findDataFormField(uint8_t* buffer, const string& field)
{
	// Find first Content-Disposition: field
	uint8_t* b = buffer;
	uint8_t* ptr = b;
	const uint8_t* ptr_end = m_buffer + m_size;
	string name = "\"" + field + "\"";
	string find = "form-data; name=" + name;
	bool found = false;

	while (ptr < ptr_end)
	{
		// Look for boundary in content data
		char *boundaryEnd = strstr((char *)ptr, m_boundary.c_str());
		if (boundaryEnd == NULL)
		{
			// No boundary, return NULL
			return NULL;
		}

		// Point to end of boundary
		ptr += m_boundary.length();

		// Skip single \r\n
		b = this->skipSeparator(ptr);

		ptr = (uint8_t *)strstr((char *)b, "Content-Disposition:");
		if (ptr == NULL)
		{
			break;
		}

		b = ptr + strlen("Content-Disposition:");

		// Look for "form-data; " and "name=" as per input field
		ptr = (uint8_t *)strstr((char *)b, find.c_str());

		// Given field name found ?
		if (ptr != NULL)
		{
			// Point to the end of mathed string
			ptr += find.length();

			found = true;
			break;
		}
		else
		{
			// Field name not found: look for next boundary after \r\n
			for (; b < ptr_end; b++)
			{
				// Look for \r\n
				if ((b + 2) != NULL && (*b == CR && *(b + 1) == LF))
				{
					if (strstr((char *)(b + 2), m_boundary.c_str()) != NULL)
					{
						// Look for boundary
						uint8_t *foundBoundary = (uint8_t *)strstr((char *)(b + 2), m_boundary.c_str());

						if (foundBoundary)
						{
							b = foundBoundary;
							break;
						}
					}
				}
			}
			ptr = b;
		}
	}

	return (found ? ptr : NULL);
}

/**
 * Fetch content data uploaded without file, example
 * curl -v -v -v --output - -X POST -F 'attributes={"name": "B1", "type": "model"}' 127.0.0.1:43605/fledge/south/uploadA
 *
 * @param field		The field name to fetch
 * @param data		The value reference to fill on success
 */
void FormData::getUploadedData(const string &field, FieldValue& data)
{
	// Point to buffer start
	uint8_t* b = (uint8_t *)m_buffer;

	// Get field name if it exists
	uint8_t* ptr = this->findDataFormField(b, field);
	if (ptr == NULL)
	{
		return;
	}

	b = ptr;
	uint8_t *endContent = this->getContentEnd(b);

	// Look for Content-Type, if existent within the 
	// same part of the message, i.e. not beyond endContent
	ptr = (uint8_t *)strstr((char *)b, "Content-Type:");
	if (ptr != NULL && ptr < endContent)
	{
		b = ptr + strlen("Content-Type:");
	}

	// Check for \r\n sequence
	b = this->skipDoubleSeparator(b);

	// Content starts here
	uint8_t *startContent = b;

	// Find end of content
	if (endContent)
	{
		// Set output data
		// Buffer start and size
		data.start = startContent;
		data.size = (size_t)(endContent - startContent);
	}
	else
	{
		Logger::getLogger()->error("Closing boundary not found for data content");
	}
}

/**
 * Fetch content data uploaded as file, example
 * curl -v -v -v --output - -X POST -F "bucket=@/some_path/file.bin" 127.0.0.1:43605/fledge/south/uploadA
 *
 * @param field		The field name (filename type) to fetch
 * @param data		The value reference to fill on success
 */
void FormData::getUploadedFile(const string& field, FieldValue& data)
{
	// Point to buffer start
	uint8_t* b = (uint8_t *)m_buffer;

	// Get field name if it exists
	uint8_t* ptr = findDataFormField(b, field);
	if (ptr == NULL)
	{
		return;
	}

	b = ptr;

	// Check for ';' after name'
	if (*b != ';')
	{
		return;
	}

	// Look for filename
	ptr = (uint8_t *)strstr((char *)b, "filename=");
	if (ptr == NULL)
	{
		return;
	}
	b = ptr + strlen("filename=");

	// Look for Content-Type
	ptr = (uint8_t *)strstr((char *)b, "Content-Type:");
	if (ptr == NULL)
	{
		return;
	}

	// Get filename
	string fileName;
	if (*(ptr - 2) == CR && (*(ptr - 1) == LF))
	{
		size_t fNameSize = (ptr - 2) - b;
		// Skip leading an trailing '"' 
		if (*b == '"')
		{
			// Filename starts after '"'
			b++;
			// Size -i 1
			fNameSize--;
		}
		if (*(ptr - 2 - 1) == '"')
		{
			// Size - 1
			fNameSize--;
		}

		// Set filename as in uploaded content
		// Caller might use this or select another name
		// while saving the content into a file
		fileName.assign((char *)b, fNameSize);
	}

	b = ptr + strlen("Content-Type:");

	// Check for \r\n sequence
	b = this->skipDoubleSeparator(b);

	// File content starts here
	uint8_t *startContent = b;

	// Find end of content
	uint8_t *endContent = this->getContentEnd(b);
	if (endContent)
	{
		// Set output data
		// Buffer start and size
		data.start = startContent;
		data.size = (size_t)(endContent - startContent);
		// Set filename
		data.filename = fileName;
	}
	else
	{
		Logger::getLogger()->error("Closing boundary not found for file content");
	}
}

/**
 * Save the uploaded file
 *
 * @param v	The Field value data
 * @return	Returns true if the file was succesfully saved
 */
bool FormData::saveFile(FormData::FieldValue& v, const string& fileName)
{
	Logger::getLogger()->debug("Uploaded filename is '%s'", v.filename.c_str());

	// v.filename holds the file name as per upload content
	Logger::getLogger()->debug("Saving uploaded file as '%s', size is %ld bytes",
				fileName.c_str(), v.size);

	// Create file
	int fd = open(fileName.c_str(),
			O_RDWR | O_CREAT | O_TRUNC,
			(mode_t)0644);
	if (fd == -1)
	{
		// An error occurred
		char errBuf[128];
		char *e = strerror_r(errno, errBuf, sizeof(errBuf));
		Logger::getLogger()->error("Error while creating filename '%s': %s",
					fileName.c_str(), e);

		return false;
	}

	// Write file from v.start, v.size bytes
	if (write(fd, (const void *)v.start, v.size) == -1)
	{
		// An error occurred
		char errBuf[128];
		char *e = strerror_r(errno, errBuf, sizeof(errBuf));
		Logger::getLogger()->error("Error while writing to file '%s': %s",
					fileName.c_str(), e);
		close(fd);
		return false;
	}

	// Close file
	close(fd);

	return true;
}


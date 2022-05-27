#ifndef _FORM_DATA_H
#define _FORM_DATA_H
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

#include <logger.h>
#include <server_http.hpp>

#define CR '\r'
#define LF '\n'

/**
 * This class represents a parsed HTTP form data uploaded
 * to SimpleWeb::Server<SimpleWeb::HTTP
 *
 * FormData::FieldValue holds the field value as buffer start, size
 * and filename if data comes form a file upload
 *
 * FormData holds the input buffer, size and boundary multipart data
 *
 * Public methods fetch value of a given field name
 * and save file to filesystem
 */
class FormData {
	public:
		class FieldValue {
			public:
				FieldValue()
				{
					size = 0;
					start = NULL;
				};
				const uint8_t*  start;
				size_t		size;
				std::string	filename;
		};

	public:
		FormData(std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Request> request);
		void		getUploadedData(const std::string& field, FieldValue& data);
		void		getUploadedFile(const std::string& field, FieldValue& data);
		bool		saveFile(FieldValue& b, const std::string& fileName);

	private:
		uint8_t*	skipSeparator(uint8_t *b);
		uint8_t*	skipDoubleSeparator(uint8_t *b);
		uint8_t*	getContentEnd(uint8_t *b);
		uint8_t*	findDataFormField(uint8_t* buffer, const std::string& field);

	private:
		const uint8_t*	m_buffer; 	// pointer to already allocated buffer data
		size_t		m_size; 	// buffer size
		std::string	m_boundary;	// multipart boundary
};
#endif

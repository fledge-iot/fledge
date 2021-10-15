#ifndef _BASE64_DATA_BUFFER_H_
#define _BASE64_DATA_BUFFER_H_
/*
 * Fledge Base64DataBuffer encoding
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <databuffer.h>
#include <string>
#include <stdexcept>
#include <base64.h>

/**
 * The Base64DataBuffer class provide functionality on top of the
 * simple DataBuffer class that is used to encode the buffer in
 * base64 such that it may be stored as string data.
 */
class Base64DataBuffer : public DataBuffer {

	public:
		Base64DataBuffer(const std::string& encoded);
  		std::string 		encode();
};
#endif

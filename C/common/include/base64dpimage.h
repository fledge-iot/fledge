#ifndef _BASE64_DPIMAGE_H_
#define _BASE64_DPIMAGE_H_
/*
 * Fledge Base64 encoded data point image
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <dpimage.h>
#include <string>
#include <stdexcept>
#include <base64.h>

/**
 * The Base64DPImage provide functionality on top of the 
 * simple DPImage class that is used to encode the buffer in
 * base64 such that it may be stored as string data.
 */
class Base64DPImage : public DPImage {
	public:
		Base64DPImage(const std::string& encoded);
  		std::string 		encode();
};
#endif

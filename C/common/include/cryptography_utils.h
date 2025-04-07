#ifndef _CRYPTOGRAPHY_UTILS_H
#define _CRYPTOGRAPHY_UTILS_H
/*
 * FogLAMP utilities functions for generating cryptographic hash
 *
 * Copyright (c) 2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <openssl/sha.h>
#include <openssl/opensslv.h>
#ifdef OPENSSL_VERSION_NUMBER
	#if OPENSSL_VERSION_NUMBER >= 0x30000000L
	#include <openssl/evp.h>
	#endif
#endif

#include <string>
std::string compute_sha256(const std::string& input);

#endif


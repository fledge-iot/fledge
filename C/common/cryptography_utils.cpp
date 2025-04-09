/*
 * FogLAMP utilities functions for generating cryptographic hash
 *
 * Copyright (c) 2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <sstream>
#include <iomanip>
#include "cryptography_utils.h"

/*
*
* Generates SHA256 Hash
*
* @param input	JSON string for the reading
* @return SHA256 Hash String
*/

std::string compute_sha256(const std::string& input)
{
    #ifdef OPENSSL_VERSION_NUMBER
      #if OPENSSL_VERSION_NUMBER >= 0x30000000L
        // Code for OpenSSL 3.0.x
        unsigned char digest[SHA256_DIGEST_LENGTH];
        EVP_MD_CTX *ctx = EVP_MD_CTX_new();
        
        if (!ctx) {
            throw std::runtime_error("Failed to create OpenSSL EVP_MD_CTX");
        }

        if (EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr) != 1 ||
            EVP_DigestUpdate(ctx, input.data(), input.size()) != 1 ||
            EVP_DigestFinal_ex(ctx, digest, nullptr) != 1) 
        {
            EVP_MD_CTX_free(ctx);
            throw std::runtime_error("OpenSSL SHA-256 computation failed");
        }

        EVP_MD_CTX_free(ctx);

        std::ostringstream ss;
        for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) 
        {
            ss << std::setw(2) << std::setfill('0') << std::hex << (int)digest[i];
        }

        return ss.str();
      #else
        // Code for OpenSSL 1.1.x
        unsigned char digest[SHA256_DIGEST_LENGTH];
        SHA256_CTX sha256Context;
        SHA256_Init(&sha256Context);
        SHA256_Update(&sha256Context, input.c_str(), input.length());
        SHA256_Final(digest, &sha256Context);
        std::ostringstream ss;
        for (int i = 0; i < SHA256_DIGEST_LENGTH; i++)
        {
            ss << std::setw(2) << std::setfill('0') << std::hex << (int)digest[i];
        }
        return ss.str();
      #endif
    #endif
    
}

std::string compute_md5(const std::string& input)
{
#ifdef OPENSSL_VERSION_NUMBER
  #if OPENSSL_VERSION_NUMBER >= 0x30000000L
    // Code for OpenSSL 3.0.x
    unsigned char digest[MD5_DIGEST_LENGTH];
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();

    if (!ctx) {
        throw std::runtime_error("Failed to create OpenSSL EVP_MD_CTX");
    }

    if (EVP_DigestInit_ex(ctx, EVP_md5(), nullptr) != 1 ||
        EVP_DigestUpdate(ctx, input.data(), input.size()) != 1 ||
        EVP_DigestFinal_ex(ctx, digest, nullptr) != 1) 
    {
        EVP_MD_CTX_free(ctx);
        throw std::runtime_error("OpenSSL MD5 computation failed");
    }

    EVP_MD_CTX_free(ctx);

    std::ostringstream ss;
    for (int i = 0; i < MD5_DIGEST_LENGTH; i++) 
    {
        ss << std::setw(2) << std::setfill('0') << std::hex << (int)digest[i];
    }

    return ss.str();
  #else
    // Code for OpenSSL 1.1.x
    unsigned char digest[MD5_DIGEST_LENGTH];
    MD5_CTX md5Context;
    MD5_Init(&md5Context);
    MD5_Update(&md5Context, input.c_str(), input.length());
    MD5_Final(digest, &md5Context);

    std::ostringstream ss;
    for (int i = 0; i < MD5_DIGEST_LENGTH; i++)
    {
        ss << std::setw(2) << std::setfill('0') << std::hex << (int)digest[i];
    }

    return ss.str();
  #endif
#endif
}

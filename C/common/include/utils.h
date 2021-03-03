#ifndef _FLEDGE_UTILS_H
#define _FLEDGE_UTILS_H
/*
 * Fledge general utilities
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <string>

#define _FLEDGE_ROOT_PATH    "/usr/local/fledge"

using namespace std;

/**
 * Return Fledge root dir
 *
 * Return current value of FLEDGE_ROOT env var or
 * default path _FLEDGE_ROOT_PATH
 *
 * @return	Return Fledge root dir
 */
static const string getRootDir()
{
	const char* rootDir = getenv("FLEDGE_ROOT");
	return (rootDir ? string(rootDir) : string(_FLEDGE_ROOT_PATH));
}

/**
 * Return Fledge data dir
 *
 * Return current value of FLEDGE_DATA env var or
 * default value: getRootDir + /data
 *
 * @return	Return Fledge data dir
 */
static const string getDataDir()
{
	const char* dataDir = getenv("FLEDGE_DATA");
	return (dataDir ? string(dataDir) : string(getRootDir() + "/data"));
}

#endif

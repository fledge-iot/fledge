#ifndef _FOGLAMP_UTILS_H
#define _FOGLAMP_UTILS__H
/*
 * FogLAMP general utilities
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <string>

#define _FOGLAMP_ROOT_PATH    "/usr/local/foglamp"

using namespace std;

/**
 * Return FogLAMP root dir
 *
 * Return current value of FOGLAMP_ROOT env var or
 * default path _FOGLAMP_ROOT_PATH
 *
 * @return	Return FogLAMP root dir
 */
const string getRootDir()
{
	const char* rootDir = getenv("FOGLAMP_ROOT");
	return (rootDir ? string(rootDir) : string(_FOGLAMP_ROOT_PATH));
}

/**
 * Return FogLAMP data dir
 *
 * Return current value of FOGLAMP_DATA env var or
 * default value: getRootDir + /data
 *
 * @return	Return FogLAMP data dir
 */
const string getDataDir()
{
	const char* dataDir = getenv("FOGLAMP_DATA");
	return (dataDir ? string(dataDir) : string(getRootDir() + "/data"));
}

#endif

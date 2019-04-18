/*
 * Utility to extract plugin snapshot tar archive
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <errno.h>

extern int errno;

/**
 * Check whether file/dir exists within FOGLAMP_ROOT
 *
 * @param rootdir	FOGLAMP_ROOT path
 * @param file		relative path of file or dir inside FOGLAMP_ROOT
 */
bool checkFile(char *rootdir, char *file)
{
	char path[256];
	snprintf(path, sizeof(path), "%s/%s", rootdir, file);
	return (access(path, F_OK) == 0);
}

/**
 * Extract files from within plugin snapshot tar archive
 *
 *    Usage: extract_plugin_snapshot <plugin snapshot archive>
 *
 * @param argv[1]  relative/absolute path of plugin snapshot archive
 */
int main(int argc, char *argv[])
{
	if(argc < 2)
	{
		printf("Usage: %s <archive filename>\n", argv[0]);
		return 1;
	}

	char *rootdir = getenv("FOGLAMP_ROOT");
	if (!rootdir || rootdir[0]==0)
	{
		printf("Unable to find path where archive is to be extracted\n");
		return 2;
	}
	struct stat sb;
	stat(rootdir, &sb);
	if ((sb.st_mode & S_IFMT) != S_IFDIR)
	{
		printf("Unable to find path where archive is to be extracted\n");
		return 2;
	}
	
	if (!checkFile(rootdir, (char *) "bin/foglamp") || 
		!checkFile(rootdir, (char *) "services/foglamp.services.storage") || 
		!checkFile(rootdir, (char *) "python/foglamp/services/core/routes.py") || 
		!checkFile(rootdir, (char *) "lib/libcommon-lib.so") || 
		!checkFile(rootdir, (char *) "tasks/sending_process"))
	{
		printf("Unable to find foglamp insallation\n");
		return 2;
	}
	
	char *args[]={(char *) "/bin/tar", (char *) "-C", (char *) "PLACEHOLDER", (char *) "-xf", (char *) "PLACEHOLDER", NULL}; 
	args[2] = rootdir;
	args[4] = argv[1];

	errno = 0;
	int rc = execvp(args[0], args);
	if (rc != 0)
	{
		printf("execvp failed: errno=%s\n", strerror(errno));
		return 3;
	}

	return 0;
}


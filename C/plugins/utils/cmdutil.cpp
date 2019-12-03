/*
 * Utility to run some commands for fledge as root using setuid
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
 * Check whether file/dir exists within FLEDGE_ROOT
 *
 * @param rootdir	FLEDGE_ROOT path
 * @param file		relative path of file or dir inside FLEDGE_ROOT
 */
bool checkFile(char *rootdir, char *file)
{
	char path[256];
	snprintf(path, sizeof(path), "%s/%s", rootdir, file);
	return (access(path, F_OK) == 0);
}

const char *cmds[] = {"tar-extract", "cp", "rm", "pip3-pkg", "pip3-req", "mkdir"};

typedef enum {
	TAR_EXTRACT,
	CP,
	RM,
	PIP3_PKG,
	PIP3_REQ,
	MKDIR
} cmdtype_t;

char *argsArray[][6] = {
	{(char *) "/bin/tar", (char *) "-C", 	(char *) "PLACEHOLDER", (char *) "-xf", 		(char *) "PLACEHOLDER", NULL},
	{(char *) "/bin/cp",  (char *) "-r", 	(char *) "PLACEHOLDER", (char *) "PLACEHOLDER", NULL, 					NULL},
	{(char *) "/bin/rm",  (char *) "-rf", 	(char *) "PLACEHOLDER", NULL, 					NULL, 					NULL},
	{(char *) "pip3", 	(char *) "install", (char *) "PLACEHOLDER", (char *) "--no-cache-dir", NULL, 				NULL},
	{(char *) "pip3", 	(char *) "install", (char *) "-Ir", 		(char *) "PLACEHOLDER",	(char *) "--no-cache-dir", NULL},
	{(char *) "mkdir",  (char *) "-p", 		(char *) "PLACEHOLDER", NULL, 					NULL, 					NULL}
};

int getCmdType(const char *cmd)
{
	for (int i=0; i<sizeof(cmds)/sizeof(const char *); i++)
		if (strcmp(cmd, cmds[i])==0)
			return i;
	
	return -1;
}

/**
 * Run some shell commands, if setuid bit is set, these cmds are run as root user
 *
 *    Usage: cmdutil <cmd> <params>
 *
 *		Example command to execute						Way to invoke cmdutil to do so
 *		--------------------------						-------------------------------
 * 		sudo tar -C $FLEDGE_ROOT -xf abc.tar.gz		cmdutil tar-extract abc.tar.gz
 *		sudo cp -r abc $FLEDGE_ROOT/xyz				cmdutil cp abc xyz
 *		sudo rm -rf $FLEDGE_ROOT/abc					cmdutil rm abc
 *
 *		sudo pip3 install aiocoap==0.3 --no-cache-dir	cmdutil pip3-pkg aiocoap==0.3
 *		sudo pip3 install -Ir requirements.txt --no-cache-dir	cmdutil pip3-req requirements.txt
 *
 *		sudo mkdir -p $FLEDGE_ROOT/abc					cmdutil mkdir abc
 */
int main(int argc, char *argv[])
{
	if(argc < 2)
	{
		printf("Incorrect usage\n");
		return 1;
	}

	char *rootdir = getenv("FLEDGE_ROOT");
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
	
	if (!checkFile(rootdir, (char *) "bin/fledge") || 
		!checkFile(rootdir, (char *) "services/fledge.services.storage") || 
		!checkFile(rootdir, (char *) "python/fledge/services/core/routes.py") || 
		!checkFile(rootdir, (char *) "lib/libcommon-lib.so") || 
		!checkFile(rootdir, (char *) "tasks/sending_process"))
	{
		printf("Unable to find fledge insallation\n");
		return 2;
	}

	int cmdtype = getCmdType(argv[1]);
	//printf("cmdtype=%d\n", cmdtype);
	if(cmdtype == -1)
	{
		printf("Unidentified command\n");
		return 3;
	}

	char *args[6];
	for(int i=0; i<6; i++)
		args[i] = argsArray[cmdtype][i];
	char buf[128];
	switch (cmdtype)
	{
		case TAR_EXTRACT:
				args[2] = rootdir;
				args[4] = argv[2];
			break;
		case CP:
				args[2] = argv[2];
				snprintf(buf, sizeof(buf), "%s/%s", rootdir, argv[3]);
				buf[sizeof(buf)-1] = '\0'; // force null terminate
				args[3] = buf;
			break;
		case RM:
				snprintf(buf, sizeof(buf), "%s/%s", rootdir, argv[2]);
				buf[sizeof(buf)-1] = '\0'; // force null terminate
				args[2] = buf;
			break;
		case PIP3_PKG:
				args[2] = argv[2];
			break;
		case PIP3_REQ:
				args[3] = argv[2];
			break;
		case MKDIR:
				snprintf(buf, sizeof(buf), "%s/%s", rootdir, argv[2]);
				buf[sizeof(buf)-1] = '\0'; // force null terminate
				args[2] = buf;
			break;
		default:
			printf("Unidentified command\n");
			return 3;
	}

	//printf("cmd=%s %s %s %s %s %s\n", args[0], args[1], args[2], args[3]?args[3]:"", args[4]?args[4]:"", args[5]?args[5]:"");

	errno = 0;
	int rc = execvp(args[0], args);
	if (rc != 0)
	{
		printf("execvp failed: rc=%d, errno %d=%s\n", rc, errno, strerror(errno));
		return rc;
	}
	
	return 0;
}


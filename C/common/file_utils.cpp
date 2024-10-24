/*
 * Fledge utilities functions for handling files and directories
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Ray Verhoeff
 */

#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <ftw.h>
#include <stdexcept>
#include "file_utils.h"

/**
 * Callback for Linux file walk routine 'nftw'
 *
 * @param filePath	File full path
 * @param sb		struct stat to hold file information
 * @param typeflag	File type flag: FTW_F = file, FTW_D = directory
 * @param ftwbuf	struct FTW to hold name offset and file depth
 * @return			Zero if successful
 */
static int fileDeleteCallback(const char *filePath, const struct stat *sb, int typeflag, struct FTW *ftwbuf)
{
    return remove(filePath);
}

/**
 * Copy a file
 * 
 * @param to	Full path of the destination file
 * @param from	Full path of the source file
 * @return		Zero if successful
 */
int copyFile(const char *to, const char *from)
{
	int fd_to, fd_from;
	char buf[4096];
	ssize_t nread;
	int saved_errno;

	fd_from = open(from, O_RDONLY);
	if (fd_from < 0)
		return -1;

	fd_to = open(to, O_WRONLY | O_CREAT | O_EXCL, 0666);
	if (fd_to < 0)
		goto out_error;

	while (nread = read(fd_from, buf, sizeof buf), nread > 0)
	{
		char *out_ptr = buf;
		ssize_t nwritten;

		do
		{
			nwritten = write(fd_to, out_ptr, nread);

			if (nwritten >= 0)
			{
				nread -= nwritten;
				out_ptr += nwritten;
			}
			else if (errno != EINTR)
			{
				goto out_error;
			}
		} while (nread > 0);
	}

	if (nread == 0)
	{
		if (close(fd_to) < 0)
		{
			fd_to = -1;
			goto out_error;
		}
		close(fd_from);

		/* Success! */
		return 0;
	}

out_error:
	saved_errno = errno;

	close(fd_from);
	if (fd_to >= 0)
		close(fd_to);

	errno = saved_errno;
	return -1;
}

/**
 * Create a single directory.
 * This routine cannot create a directory tree from a full path.
 * This routine throws a std::runtime_error exception if the directory cannot be created.
 *
 * @param directoryName		Full path of the directory to create
 */
void createDirectory(const std::string &directoryName)
{
	const char *path = directoryName.c_str();
	struct stat sb;
	if (stat(path, &sb) != 0)
	{
		int retcode;
		if ((retcode = mkdir(path, S_IRWXU | S_IRWXG)) != 0)
		{
			std::string exceptionMessage = "Unable to create directory " + directoryName + ": error: " + std::to_string(retcode);
			throw std::runtime_error(exceptionMessage.c_str());
		}
	}
}

/**
 * Remove a directory with all subdirectories and files
 *
 * @param path		Full path of the directory
 * @return			Zero if successful
 */
int removeDirectory(const char *path)
{
    return nftw(path, fileDeleteCallback, 64, FTW_DEPTH | FTW_PHYS);
}

/*
 * Fledge utilities functions for handling files and directories
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Ray Verhoeff
 */

#pragma once
#include <string>

int copyFile(const char *to, const char *from);
void createDirectory(const std::string &directoryName);
int removeDirectory(const char *path);

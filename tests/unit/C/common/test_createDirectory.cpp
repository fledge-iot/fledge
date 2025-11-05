/*
 * unit tests - FOGL-9345 : Improve createDirectory utility routine
 *
 * Copyright (c) 2025 Dianomic Systems, Inc.
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <gtest/gtest.h>
#include <file_utils.h>
#include <exception>

using namespace std;



TEST(TEST_DIRECTORY, PERMISSION_DENIED)
{
    std::string directoryName = "/root/nopermission";
    try {
        createDirectory(directoryName);
        FAIL() << "Expected std::runtime_error";
    }
    catch(std::runtime_error const & err) {
        EXPECT_EQ(err.what(),std::string("Unable to create directory /root/nopermission: error: -1"));
    }
    catch(...) {
        FAIL() << "Expected std::runtime_error";
    }
}

TEST(TEST_DIRECTORY, PATH_NOT_DIRECTORY)
{
    std::string directoryName = "/lib/systemd/systemd";
    try {
        createDirectory(directoryName);
        FAIL() << "Expected std::runtime_error";
    }
    catch(std::runtime_error const & err) {
        EXPECT_EQ(err.what(),std::string("Path exists but is not a directory: /lib/systemd/systemd"));
    }
    catch(...) {
        FAIL() << "Expected std::runtime_error";
    }
}

TEST(TEST_DIRECTORY, DIRECTORY_EXISTS_OR_CREATED)
{
    std::string directoryName = "/tmp/testCreateDirFunc";
 
    createDirectory(directoryName);
    struct stat sb;
    if (stat(directoryName.c_str(), &sb) != 0)
    {
        FAIL() << "Directory " << directoryName << " could not be created";
    }

}
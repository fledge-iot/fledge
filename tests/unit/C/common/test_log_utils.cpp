#include <gtest/gtest.h>

#include "log_utils.h"

TEST(LogUtilsTest, LogWrappers)
{
    std::string text("This message is at level %s");
    ASSERT_NO_THROW(LogUtils::log_debug(text.c_str(), "debug"));
    ASSERT_NO_THROW(LogUtils::log_info(text.c_str(), "info"));
    ASSERT_NO_THROW(LogUtils::log_warn(text.c_str(), "warning"));
    ASSERT_NO_THROW(LogUtils::log_error(text.c_str(), "error"));
    ASSERT_NO_THROW(LogUtils::log_fatal(text.c_str(), "fatal"));
}
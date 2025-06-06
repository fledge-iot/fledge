/*
 * unit tests FOGL-9560 : Add log interceptor to C++ Logger class
 *
 * Copyright (c) 2025 Dianomic Systems, Inc.
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <gtest/gtest.h>
#include <logger.h>
#include <mutex>
#include <condition_variable>
using namespace std;
std::string intercepted_message = "";

Logger* log1 = Logger::getLogger();

std::condition_variable error1_condition;
std::mutex error1_mutex;
bool error1_interceptor_executed = false;

std::condition_variable warning_condition;
std::mutex warning_mutex;
bool warning_interceptor_executed = false;

std::condition_variable info_condition;
std::mutex info_mutex;
bool info_interceptor_executed = false;

std::condition_variable debug1_condition;
std::mutex debug1_mutex;
bool debug1_interceptor_executed = false;

std::condition_variable debug2_condition;
std::mutex debug2_mutex;
bool debug2_interceptor_executed = false;

std::condition_variable fatal_condition;
std::mutex fatal_mutex;
bool fatal_interceptor_executed = false;

void errorInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
     intercepted_message = "INTERCEPTED ERROR : " + message;
     error1_interceptor_executed = true;
     error1_condition.notify_one();
}

void warningInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
     intercepted_message = "INTERCEPTED WARNING : " + message;
     warning_interceptor_executed = true;
     warning_condition.notify_one();
}

void infoInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
     intercepted_message = "INTERCEPTED INFO : " + message;
     info_interceptor_executed = true;
     info_condition.notify_one();
}

void debugInterceptor_1(Logger::LogLevel level, const std::string& message, void* userData)
{
   intercepted_message = "INTERCEPTED DEBUG #1 : " + message;
   debug1_interceptor_executed = true;
   debug1_condition.notify_one();
}

void debugInterceptor_2(Logger::LogLevel level, const std::string& message, void* userData)
{
     intercepted_message = "INTERCEPTED DEBUG #2 : " + message;
     debug2_interceptor_executed = true;
     debug2_condition.notify_one();
}

void fatalInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
     intercepted_message = "INTERCEPTED FATAL : " + message;
     fatal_interceptor_executed = true;
     fatal_condition.notify_one();
}

// Test Case : Check registration and unregistration of Interceptor
TEST(TEST_LOG_INTERCEPTOR, REGISTER_UNREGISTER)
{
    std::unique_lock<std::mutex> lock(debug1_mutex);
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, nullptr));
    
    log1->debug("Testing REGISTR_UNREGISTER");
    debug1_condition.wait(lock, [this] { return debug1_interceptor_executed; });
    debug1_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing REGISTR_UNREGISTER");
    
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_1));
}


// Test Case : Check registration with null callback
TEST(TEST_LOG_INTERCEPTOR, REGISTER_NULL_CALLBACK)
{
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    log1->debug("Register NULL Callback");
    EXPECT_FALSE(log1->registerInterceptor(level1, nullptr, nullptr)); // Interceptor is not registered with null callback
}

// Test Case: Unregister Non-Registered Interceptor
TEST(TEST_LOG_INTERCEPTOR, UNREGISTER_NON_REGISTERED)
{
    // LogLevel Debug
    log1->setMinLevel("debug");

    Logger::LogLevel level = Logger::LogLevel::DEBUG; 
    EXPECT_FALSE(log1->unregisterInterceptor(level, debugInterceptor_1));  // Trying to unregister before it's registered
}


// Test Case: Multiple Interceptors for the Same Log Level
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_INTERCEPTORS_SAME_LEVEL)
{
    std::unique_lock<std::mutex> lock(debug1_mutex);
    std::unique_lock<std::mutex> lock2(debug2_mutex);
    // LogLevel Debug
    log1->setMinLevel("debug");

    Logger::LogLevel level = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1->registerInterceptor(level, debugInterceptor_1, nullptr));
    EXPECT_TRUE(log1->registerInterceptor(level, debugInterceptor_2, nullptr));
    
    log1->debug("Multiple interceptors test");
    debug1_condition.wait(lock, [this] { return debug1_interceptor_executed; });
    debug1_interceptor_executed = false; // Reset the flag for next test case

    debug2_condition.wait(lock2, [this] { return debug2_interceptor_executed; });
    debug2_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_TRUE(intercepted_message.find("INTERCEPTED DEBUG #1 : DEBUG: Multiple interceptors test") != std::string::npos || 
                intercepted_message.find("INTERCEPTED DEBUG #2 : DEBUG: Multiple interceptors test") != std::string::npos);

    EXPECT_TRUE(log1->unregisterInterceptor(level, debugInterceptor_1));
    EXPECT_TRUE(log1->unregisterInterceptor(level, debugInterceptor_2));
}

// Test Case : Check multiple registration for same log level
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_REGISTER)
{
    std::unique_lock<std::mutex> lock(debug1_mutex);
    // LogLevel Debug
    log1->setMinLevel("debug");
    usleep(500);
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, nullptr));
    
    log1->debug("Register Debug Logger");
    debug1_condition.wait(lock, [this] { return debug1_interceptor_executed; });
    debug1_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Register Debug Logger");
    
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_1));
    std::unique_lock<std::mutex> lock2(debug2_mutex);
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_2, nullptr));
    
    log1->debug("Register Debug Logger");
    debug2_condition.wait(lock2, [this] { return debug2_interceptor_executed; });
    debug2_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #2 : DEBUG: Register Debug Logger");
    
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_2));
  
}

// Test Case : Check multiple unregister 
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_UNREGISTER)
{
    std::unique_lock<std::mutex> lock(debug1_mutex);
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, nullptr));
    
    log1->debug("Testing First UNREGISTER");
    debug1_condition.wait(lock, [this] { return debug1_interceptor_executed; });
    debug1_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing First UNREGISTER");
    
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_1));
    EXPECT_FALSE(log1->unregisterInterceptor(level1, debugInterceptor_1)); // return false because interceptor already unregistered

}

// Test Case : Check registration and unregistration of Interceptor for all the supported log levels
TEST(TEST_LOG_INTERCEPTOR, ALL_LOG_LEVELS)
{
    std::unique_lock<std::mutex> debug_lk(debug1_mutex);
    std::unique_lock<std::mutex> error_lk(error1_mutex);
    std::unique_lock<std::mutex> warning_lk(warning_mutex);
    std::unique_lock<std::mutex> info_lk(info_mutex);
    std::unique_lock<std::mutex> fatal_lk(fatal_mutex);
    // LogLevel Error
    log1->setMinLevel("error");
    Logger::LogLevel level1 = Logger::LogLevel::ERROR; 
    
    EXPECT_TRUE(log1->registerInterceptor(level1, errorInterceptor, nullptr));
    
    log1->error("Testing error interceptor");
    error1_condition.wait(error_lk, [this] { return error1_interceptor_executed; });
    error1_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED ERROR : ERROR: Testing error interceptor");
    
    EXPECT_TRUE(log1->unregisterInterceptor(level1, errorInterceptor));

    // LogLevel Warning
    log1->setMinLevel("warning");
    Logger::LogLevel level2 = Logger::LogLevel::WARNING; 
    
    EXPECT_TRUE(log1->registerInterceptor(level2, warningInterceptor, nullptr));
    
    log1->warn("Testing warning interceptor");
    warning_condition.wait(warning_lk, [this] { return warning_interceptor_executed; });
    warning_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED WARNING : WARNING: Testing warning interceptor");
    
    EXPECT_TRUE(log1->unregisterInterceptor(level2, warningInterceptor));

    // LogLevel Info
    log1->setMinLevel("info");
    Logger::LogLevel level3 = Logger::LogLevel::INFO; 
    
    EXPECT_TRUE(log1->registerInterceptor(level3, infoInterceptor, nullptr));
    
    log1->info("Testing info interceptor");
    info_condition.wait(info_lk, [this] { return info_interceptor_executed; });
    info_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED INFO : INFO: Testing info interceptor");
    
    EXPECT_TRUE(log1->unregisterInterceptor(level3, infoInterceptor));

    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level4 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1->registerInterceptor(level4, debugInterceptor_1, nullptr));
    
    log1->debug("Testing debug interceptor");
    debug1_condition.wait(debug_lk, [this] { return debug1_interceptor_executed; });
    debug1_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing debug interceptor");
    
    EXPECT_TRUE(log1->unregisterInterceptor(level4, debugInterceptor_1));

    // LogLevel Debug takes care of FATAL error as well
    log1->setMinLevel("debug");
    Logger::LogLevel level5 = Logger::LogLevel::FATAL; 
    
    EXPECT_TRUE(log1->registerInterceptor(level5, fatalInterceptor, nullptr));
    
    log1->fatal("Testing fatal interceptor");
    fatal_condition.wait(fatal_lk, [this] { return fatal_interceptor_executed; });
    fatal_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED FATAL : FATAL: Testing fatal interceptor");
    
    EXPECT_TRUE(log1->unregisterInterceptor(level5, fatalInterceptor));

}

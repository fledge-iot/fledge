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

Logger* log1 = Logger::getLogger();


bool log_interceptor_executed = false;

struct LogInterceptorData {
    std::mutex cond_mtx;
    std::condition_variable cv1;
    std::string intercepted_message;
};

// Callback Interceptor functions
void errorInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(((LogInterceptorData*)userData)->cond_mtx);
    ((LogInterceptorData*)userData)->intercepted_message = "INTERCEPTED ERROR : " + message;
    log_interceptor_executed = true;
    ((LogInterceptorData*)userData)->cv1.notify_one();
}

void warningInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(((LogInterceptorData*)userData)->cond_mtx);
    ((LogInterceptorData*)userData)->intercepted_message= "INTERCEPTED WARNING : " + message;
    log_interceptor_executed = true;
    ((LogInterceptorData*)userData)->cv1.notify_one();
}

void infoInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(((LogInterceptorData*)userData)->cond_mtx);
    ((LogInterceptorData*)userData)->intercepted_message = "INTERCEPTED INFO : " + message;
    log_interceptor_executed = true;
    ((LogInterceptorData*)userData)->cv1.notify_one();
}

void debugInterceptor_1(Logger::LogLevel level, const std::string& message, void* userData)
{
   std::unique_lock<std::mutex> lock(((LogInterceptorData*)userData)->cond_mtx);
   ((LogInterceptorData*)userData)->intercepted_message= "INTERCEPTED DEBUG #1 : " + message;
   log_interceptor_executed = true;
   ((LogInterceptorData*)userData)->cv1.notify_one();
}

void debugInterceptor_2(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(((LogInterceptorData*)userData)->cond_mtx);
    ((LogInterceptorData*)userData)->intercepted_message = "INTERCEPTED DEBUG #2 : " + message;
    log_interceptor_executed = true;
    ((LogInterceptorData*)userData)->cv1.notify_one();
}

void fatalInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(((LogInterceptorData*)userData)->cond_mtx);
    ((LogInterceptorData*)userData)->intercepted_message = "INTERCEPTED FATAL : " + message;
    log_interceptor_executed = true;
    ((LogInterceptorData*)userData)->cv1.notify_one();
}

// Test Case : Check registration and unregistration of Interceptor
TEST(TEST_LOG_INTERCEPTOR, REGISTER_UNREGISTER)
{
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    LogInterceptorData userData;
    
    
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, &userData));
    {
        std::unique_lock<std::mutex> lock1(userData.cond_mtx);
        log1->debug("Testing REGISTER_UNREGISTER");
        userData.cv1.wait(lock1, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData.intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing REGISTER_UNREGISTER");
    }
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
    LogInterceptorData userData1;
    LogInterceptorData userData2;
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1->registerInterceptor(level, debugInterceptor_1, &userData1));
    EXPECT_TRUE(log1->registerInterceptor(level, debugInterceptor_2, &userData2));
    {
        std::unique_lock<std::mutex> lock1(userData1.cond_mtx);
        std::unique_lock<std::mutex> lock2(userData2.cond_mtx);
        log1->debug("Multiple interceptors test");
        userData1.cv1.wait(lock1, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData1.intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Multiple interceptors test");

        userData2.cv1.wait(lock2, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData2.intercepted_message, "INTERCEPTED DEBUG #2 : DEBUG: Multiple interceptors test");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level, debugInterceptor_1));
    EXPECT_TRUE(log1->unregisterInterceptor(level, debugInterceptor_2));
}


// Test Case : Check multiple registration for same log level
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_REGISTER)
{
    LogInterceptorData userData1;
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, &userData1));
    {
        std::unique_lock<std::mutex> lock1(userData1.cond_mtx);
        log1->debug("Register Debug Logger");
        userData1.cv1.wait(lock1, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData1.intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Register Debug Logger");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_1));
    LogInterceptorData userData2;
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_2, &userData2));
    {
        std::unique_lock<std::mutex> lock2(userData2.cond_mtx);
        log1->debug("Register Debug Logger");
        userData2.cv1.wait(lock2, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData2.intercepted_message, "INTERCEPTED DEBUG #2 : DEBUG: Register Debug Logger");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_2));
}

// Test Case : Check multiple unregister 
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_UNREGISTER)
{
    LogInterceptorData userData1;
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, &userData1));
    {
        std::unique_lock<std::mutex> lock1(userData1.cond_mtx);
        log1->debug("Testing First UNREGISTER");
        userData1.cv1.wait(lock1, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData1.intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing First UNREGISTER");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_1));
    EXPECT_FALSE(log1->unregisterInterceptor(level1, debugInterceptor_1)); // return false because interceptor already unregistered

}

// Test Case : Check registration and unregistration of Interceptor for all the supported log levels
TEST(TEST_LOG_INTERCEPTOR, ALL_LOG_LEVELS)
{
    LogInterceptorData userData1;

    // LogLevel Error
    log1->setMinLevel("error");
    Logger::LogLevel level1 = Logger::LogLevel::ERROR; 
    EXPECT_TRUE(log1->registerInterceptor(level1, errorInterceptor, &userData1));
    {
        std::unique_lock<std::mutex> lock1(userData1.cond_mtx);
        log1->error("Testing error interceptor");
        userData1.cv1.wait(lock1, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData1.intercepted_message, "INTERCEPTED ERROR : ERROR: Testing error interceptor");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level1, errorInterceptor));

    // LogLevel Warning
    LogInterceptorData userData2;
    log1->setMinLevel("warning");
    Logger::LogLevel level2 = Logger::LogLevel::WARNING; 
    EXPECT_TRUE(log1->registerInterceptor(level2, warningInterceptor, &userData2));
    {
        std::unique_lock<std::mutex> lock1(userData2.cond_mtx);
        log1->warn("Testing warning interceptor");
        userData2.cv1.wait(lock1, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData2.intercepted_message, "INTERCEPTED WARNING : WARNING: Testing warning interceptor");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level2, warningInterceptor));

    // LogLevel Info
    LogInterceptorData userData3;
    log1->setMinLevel("info");
    Logger::LogLevel level3 = Logger::LogLevel::INFO; 
    
    EXPECT_TRUE(log1->registerInterceptor(level3, infoInterceptor, &userData3));
    {
        std::unique_lock<std::mutex> lock1(userData3.cond_mtx);
        log1->info("Testing info interceptor");
        userData3.cv1.wait(lock1, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData3.intercepted_message, "INTERCEPTED INFO : INFO: Testing info interceptor");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level3, infoInterceptor));

    // LogLevel Debug
    LogInterceptorData userData4;
    log1->setMinLevel("debug");
    Logger::LogLevel level4 = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1->registerInterceptor(level4, debugInterceptor_1, &userData4));
    {
        std::unique_lock<std::mutex> lock1(userData4.cond_mtx);
        log1->debug("Testing debug interceptor");
        userData4.cv1.wait(lock1, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData4.intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing debug interceptor");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level4, debugInterceptor_1));

    // LogLevel Debug takes care of FATAL error as well
    LogInterceptorData userData5;
    log1->setMinLevel("debug");
    Logger::LogLevel level5 = Logger::LogLevel::FATAL; 
    EXPECT_TRUE(log1->registerInterceptor(level5, fatalInterceptor, &userData5));
    {
        std::unique_lock<std::mutex> lock1(userData5.cond_mtx);
        log1->fatal("Testing fatal interceptor");
        userData5.cv1.wait(lock1, [] { return log_interceptor_executed; });
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(userData5.intercepted_message, "INTERCEPTED FATAL : FATAL: Testing fatal interceptor");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level5, fatalInterceptor));
}


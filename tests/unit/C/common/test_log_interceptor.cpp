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

std::condition_variable cv1;
std::condition_variable cv2;

std::mutex cond_mtx1;
std::mutex cond_mtx2;

bool log_interceptor_executed = false;

// Callback Interceptor functions
void errorInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(cond_mtx1);
    *(std::string*)userData = "INTERCEPTED ERROR : " + message;
    log_interceptor_executed = true;
    cv1.notify_one();
}

void warningInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(cond_mtx2);
    *(std::string*)userData = "INTERCEPTED WARNING : " + message;
    log_interceptor_executed = true;
    cv1.notify_one();
}

void infoInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(cond_mtx1);
    *(std::string*)userData = "INTERCEPTED INFO : " + message;
    log_interceptor_executed = true;
    cv1.notify_one();
}

void debugInterceptor_1(Logger::LogLevel level, const std::string& message, void* userData)
{
   std::unique_lock<std::mutex> lock(cond_mtx1);
   *(std::string*)userData = "INTERCEPTED DEBUG #1 : " + message;
   log_interceptor_executed = true;
   cv1.notify_one();
}

void debugInterceptor_2(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(cond_mtx2);
    *(std::string*)userData = "INTERCEPTED DEBUG #2 : " + message;
    log_interceptor_executed = true;
    cv2.notify_one();
}

void fatalInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(cond_mtx1);
    *(std::string*)userData = "INTERCEPTED FATAL : " + message;
    log_interceptor_executed = true;
    cv1.notify_one();
}

// Test Case : Check registration and unregistration of Interceptor
TEST(TEST_LOG_INTERCEPTOR, REGISTER_UNREGISTER)
{
    std::string debugInterceptorMsg1 = "";
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, &debugInterceptorMsg1));
    {
        std::unique_lock<std::mutex> lock1(cond_mtx1);
        log1->debug("Testing REGISTER_UNREGISTER");
        while(!log_interceptor_executed)
        {
            cv1.wait_for(lock1, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg1, "INTERCEPTED DEBUG #1 : DEBUG: Testing REGISTER_UNREGISTER");
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
    std::string debugInterceptorMsg1 = "";
    std::string debugInterceptorMsg2 = "";
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1->registerInterceptor(level, debugInterceptor_1, &debugInterceptorMsg1));
    EXPECT_TRUE(log1->registerInterceptor(level, debugInterceptor_2, &debugInterceptorMsg2));
    {
        std::unique_lock<std::mutex> lock1(cond_mtx1);
        std::unique_lock<std::mutex> lock2(cond_mtx2);
        log1->debug("Multiple interceptors test");
        while(!log_interceptor_executed)
        {
            cv1.wait_for(lock1, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg1, "INTERCEPTED DEBUG #1 : DEBUG: Multiple interceptors test");

        while(!log_interceptor_executed)
        {
            cv2.wait_for(lock2, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg2, "INTERCEPTED DEBUG #2 : DEBUG: Multiple interceptors test");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level, debugInterceptor_1));
    EXPECT_TRUE(log1->unregisterInterceptor(level, debugInterceptor_2));
}


// Test Case : Check multiple registration for same log level
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_REGISTER)
{
    std::string debugInterceptorMsg1 = "";
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, &debugInterceptorMsg1));
    {
        std::unique_lock<std::mutex> lock1(cond_mtx1);
        log1->debug("Register Debug Logger");
        while(!log_interceptor_executed)
        {
            cv1.wait_for(lock1, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg1, "INTERCEPTED DEBUG #1 : DEBUG: Register Debug Logger");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_1));
    std::string debugInterceptorMsg2 = "";
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_2, &debugInterceptorMsg2));
    {
        std::unique_lock<std::mutex> lock2(cond_mtx2);
        log1->debug("Register Debug Logger");
        while(!log_interceptor_executed)
        {
            cv2.wait_for(lock2, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg2, "INTERCEPTED DEBUG #2 : DEBUG: Register Debug Logger");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_2));
}

// Test Case : Check multiple unregister 
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_UNREGISTER)
{
    std::string debugInterceptorMsg1 = "";
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, &debugInterceptorMsg1));
    {
        std::unique_lock<std::mutex> lock1(cond_mtx1);
        log1->debug("Testing First UNREGISTER");
        while(!log_interceptor_executed)
        {
            cv1.wait_for(lock1, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg1, "INTERCEPTED DEBUG #1 : DEBUG: Testing First UNREGISTER");
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_1));
    EXPECT_FALSE(log1->unregisterInterceptor(level1, debugInterceptor_1)); // return false because interceptor already unregistered

}

// Test Case : Check registration and unregistration of Interceptor for all the supported log levels
TEST(TEST_LOG_INTERCEPTOR, ALL_LOG_LEVELS)
{
    std::string debugInterceptorMsg1 = "";

    // LogLevel Error
    log1->setMinLevel("error");
    Logger::LogLevel level1 = Logger::LogLevel::ERROR; 
    EXPECT_TRUE(log1->registerInterceptor(level1, errorInterceptor, &debugInterceptorMsg1));
    {
        std::unique_lock<std::mutex> lock1(cond_mtx1);
        log1->error("Testing error interceptor");
        while(!log_interceptor_executed)
        {
            cv1.wait_for(lock1, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg1, "INTERCEPTED ERROR : ERROR: Testing error interceptor");
        debugInterceptorMsg1 = ""; // Reset the message for next test case
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level1, errorInterceptor));

    // LogLevel Warning
    log1->setMinLevel("warning");
    Logger::LogLevel level2 = Logger::LogLevel::WARNING; 
    EXPECT_TRUE(log1->registerInterceptor(level2, warningInterceptor, &debugInterceptorMsg1));
    {
        std::unique_lock<std::mutex> lock1(cond_mtx1);
        log1->warn("Testing warning interceptor");
        while(!log_interceptor_executed)
        {
            cv1.wait_for(lock1, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg1, "INTERCEPTED WARNING : WARNING: Testing warning interceptor");
        debugInterceptorMsg1 = ""; // Reset the message for next test case
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level2, warningInterceptor));

    // LogLevel Info
    log1->setMinLevel("info");
    Logger::LogLevel level3 = Logger::LogLevel::INFO; 
    
    EXPECT_TRUE(log1->registerInterceptor(level3, infoInterceptor, &debugInterceptorMsg1));
    {
        std::unique_lock<std::mutex> lock1(cond_mtx1);
        log1->info("Testing info interceptor");
        while(!log_interceptor_executed)
        {
            cv1.wait_for(lock1, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg1, "INTERCEPTED INFO : INFO: Testing info interceptor");
        debugInterceptorMsg1 = ""; // Reset the message for next test case
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level3, infoInterceptor));

    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level4 = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1->registerInterceptor(level4, debugInterceptor_1, &debugInterceptorMsg1));
    {
        std::unique_lock<std::mutex> lock1(cond_mtx1);
        log1->debug("Testing debug interceptor");
        while(!log_interceptor_executed)
        {
            cv1.wait_for(lock1, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg1, "INTERCEPTED DEBUG #1 : DEBUG: Testing debug interceptor");
        debugInterceptorMsg1 = ""; // Reset the message for next test case
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level4, debugInterceptor_1));

    // LogLevel Debug takes care of FATAL error as well
    log1->setMinLevel("debug");
    Logger::LogLevel level5 = Logger::LogLevel::FATAL; 
    EXPECT_TRUE(log1->registerInterceptor(level5, fatalInterceptor, &debugInterceptorMsg1));
    {
        std::unique_lock<std::mutex> lock1(cond_mtx1);
        log1->fatal("Testing fatal interceptor");
        while(!log_interceptor_executed)
        {
            cv1.wait_for(lock1, std::chrono::seconds(1), [this] { return log_interceptor_executed; });
        }
        ASSERT_EQ(log_interceptor_executed,true);
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(debugInterceptorMsg1, "INTERCEPTED FATAL : FATAL: Testing fatal interceptor");
        debugInterceptorMsg1 = ""; // Reset the message for next test case
    }
    EXPECT_TRUE(log1->unregisterInterceptor(level5, fatalInterceptor));
}


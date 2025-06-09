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

std::condition_variable cv1;
std::condition_variable cv2;

std::mutex log_mutex1;
std::mutex log_mutex2;
std::mutex test_case_mutex;

bool log_interceptor_executed = false;

// Callback Interceptor functions
void errorInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(log_mutex1);
    intercepted_message = "INTERCEPTED ERROR : " + message;
    log_interceptor_executed = true;
    cv1.notify_one();
}

void warningInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(log_mutex1);
    intercepted_message = "INTERCEPTED WARNING : " + message;
    log_interceptor_executed = true;
    cv1.notify_one();
}

void infoInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(log_mutex1);
    intercepted_message = "INTERCEPTED INFO : " + message;
    log_interceptor_executed = true;
    cv1.notify_one();
}

void debugInterceptor_1(Logger::LogLevel level, const std::string& message, void* userData)
{
   std::unique_lock<std::mutex> lock(log_mutex1);
   intercepted_message = "INTERCEPTED DEBUG #1 : " + message;
   log_interceptor_executed = true;
   cv1.notify_one();
}

void debugInterceptor_2(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(log_mutex2);
    intercepted_message = "INTERCEPTED DEBUG #2 : " + message;
    log_interceptor_executed = true;
    cv2.notify_one();
}

void fatalInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
    std::unique_lock<std::mutex> lock(log_mutex1);
    intercepted_message = "INTERCEPTED FATAL : " + message;
    log_interceptor_executed = true;
    cv1.notify_one();
}

// Test Case : Check registration and unregistration of Interceptor
TEST(TEST_LOG_INTERCEPTOR, REGISTER_UNREGISTER)
{
    std::unique_lock<std::mutex> test_case_lock(test_case_mutex);
    intercepted_message = ""; // Reset the intercepted message
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, nullptr));
    
    {
        std::unique_lock<std::mutex> lock1(log_mutex1);
        log1->debug("Testing REGISTER_UNREGISTER");
        cv1.wait(lock1, [this] { return log_interceptor_executed; });
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing REGISTER_UNREGISTER");
    }
    
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_1));
}


// Test Case : Check registration with null callback
TEST(TEST_LOG_INTERCEPTOR, REGISTER_NULL_CALLBACK)
{
    std::unique_lock<std::mutex> test_case_lock(test_case_mutex);
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    log1->debug("Register NULL Callback");
    EXPECT_FALSE(log1->registerInterceptor(level1, nullptr, nullptr)); // Interceptor is not registered with null callback
}

// Test Case: Unregister Non-Registered Interceptor
TEST(TEST_LOG_INTERCEPTOR, UNREGISTER_NON_REGISTERED)
{
    std::unique_lock<std::mutex> test_case_lock(test_case_mutex);
    // LogLevel Debug
    log1->setMinLevel("debug");

    Logger::LogLevel level = Logger::LogLevel::DEBUG; 
    EXPECT_FALSE(log1->unregisterInterceptor(level, debugInterceptor_1));  // Trying to unregister before it's registered
}


// Test Case: Multiple Interceptors for the Same Log Level
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_INTERCEPTORS_SAME_LEVEL)
{
    std::unique_lock<std::mutex> test_case_lock(test_case_mutex);
       
    intercepted_message = ""; // Reset the intercepted message
    // LogLevel Debug
    log1->setMinLevel("debug");

    Logger::LogLevel level = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1->registerInterceptor(level, debugInterceptor_1, nullptr));
    EXPECT_TRUE(log1->registerInterceptor(level, debugInterceptor_2, nullptr));
    
    {
        std::unique_lock<std::mutex> lock1(log_mutex1);
        std::unique_lock<std::mutex> lock2(log_mutex2);

        log1->debug("Multiple interceptors test");
        cv1.wait(lock1, [this] { return log_interceptor_executed; });
        log_interceptor_executed = false; // Reset the flag for next test case

        cv2.wait(lock2, [this] { return log_interceptor_executed; });
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_TRUE(intercepted_message.find("INTERCEPTED DEBUG #1 : DEBUG: Multiple interceptors test") != std::string::npos || 
                    intercepted_message.find("INTERCEPTED DEBUG #2 : DEBUG: Multiple interceptors test") != std::string::npos);
    }

    EXPECT_TRUE(log1->unregisterInterceptor(level, debugInterceptor_1));
    EXPECT_TRUE(log1->unregisterInterceptor(level, debugInterceptor_2));
}

// Test Case : Check multiple registration for same log level
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_REGISTER)
{
    std::unique_lock<std::mutex> test_case_lock(test_case_mutex);
    
    intercepted_message = ""; // Reset the intercepted message
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, nullptr));
    
    {
        std::unique_lock<std::mutex> lock1(log_mutex1);
        
        log1->debug("Register Debug Logger");
        cv1.wait(lock1, [this] { return log_interceptor_executed; });
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Register Debug Logger");
    }
    
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_1));
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_2, nullptr));
    
    {
        std::unique_lock<std::mutex> lock2(log_mutex2);
        log1->debug("Register Debug Logger");
        cv2.wait(lock2, [this] { return log_interceptor_executed; });
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #2 : DEBUG: Register Debug Logger");
    }
    
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_2));
  
}

// Test Case : Check multiple unregister 
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_UNREGISTER)
{
    std::unique_lock<std::mutex> test_case_lock(test_case_mutex);
    intercepted_message = ""; // Reset the intercepted message
    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1->registerInterceptor(level1, debugInterceptor_1, nullptr));
    
    {
        std::unique_lock<std::mutex> lock1(log_mutex1);
        log1->debug("Testing First UNREGISTER");
        cv1.wait(lock1, [this] { return log_interceptor_executed; });
        log_interceptor_executed = false; // Reset the flag for next test case
        ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing First UNREGISTER");
    }
    
    EXPECT_TRUE(log1->unregisterInterceptor(level1, debugInterceptor_1));
    EXPECT_FALSE(log1->unregisterInterceptor(level1, debugInterceptor_1)); // return false because interceptor already unregistered

}

// Test Case : Check registration and unregistration of Interceptor for all the supported log levels
TEST(TEST_LOG_INTERCEPTOR, ALL_LOG_LEVELS)
{
    std::unique_lock<std::mutex> test_case_lock(test_case_mutex);
    std::unique_lock<std::mutex> lock1(log_mutex1);
    intercepted_message = ""; // Reset the intercepted message
    // LogLevel Error
    log1->setMinLevel("error");
    Logger::LogLevel level1 = Logger::LogLevel::ERROR; 
    
    EXPECT_TRUE(log1->registerInterceptor(level1, errorInterceptor, nullptr));
    
    log1->error("Testing error interceptor");
    cv1.wait(lock1, [this] { return log_interceptor_executed; });
    log_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED ERROR : ERROR: Testing error interceptor");
    EXPECT_TRUE(log1->unregisterInterceptor(level1, errorInterceptor));

    // LogLevel Warning
    log1->setMinLevel("warning");
    Logger::LogLevel level2 = Logger::LogLevel::WARNING; 
    
    EXPECT_TRUE(log1->registerInterceptor(level2, warningInterceptor, nullptr));
    
    log1->warn("Testing warning interceptor");
    cv1.wait(lock1, [this] { return log_interceptor_executed; });
    log_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED WARNING : WARNING: Testing warning interceptor");
    EXPECT_TRUE(log1->unregisterInterceptor(level2, warningInterceptor));

    // LogLevel Info
    log1->setMinLevel("info");
    Logger::LogLevel level3 = Logger::LogLevel::INFO; 
    
    EXPECT_TRUE(log1->registerInterceptor(level3, infoInterceptor, nullptr));
    
    log1->info("Testing info interceptor");
    cv1.wait(lock1, [this] { return log_interceptor_executed; });
    log_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED INFO : INFO: Testing info interceptor");
    EXPECT_TRUE(log1->unregisterInterceptor(level3, infoInterceptor));

    // LogLevel Debug
    log1->setMinLevel("debug");
    Logger::LogLevel level4 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1->registerInterceptor(level4, debugInterceptor_1, nullptr));
    
    log1->debug("Testing debug interceptor");
    cv1.wait(lock1, [this] { return log_interceptor_executed; });
    log_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing debug interceptor");
    EXPECT_TRUE(log1->unregisterInterceptor(level4, debugInterceptor_1));

    // LogLevel Debug takes care of FATAL error as well
    log1->setMinLevel("debug");
    Logger::LogLevel level5 = Logger::LogLevel::FATAL; 
    
    EXPECT_TRUE(log1->registerInterceptor(level5, fatalInterceptor, nullptr));
    
    log1->fatal("Testing fatal interceptor");
    cv1.wait(lock1, [this] { return log_interceptor_executed; });
    log_interceptor_executed = false; // Reset the flag for next test case
    ASSERT_EQ(intercepted_message, "INTERCEPTED FATAL : FATAL: Testing fatal interceptor");
    EXPECT_TRUE(log1->unregisterInterceptor(level5, fatalInterceptor));
}


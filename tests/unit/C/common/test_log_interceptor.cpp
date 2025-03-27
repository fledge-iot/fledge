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

using namespace std;
std::string intercepted_message = "";

void errorInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
     intercepted_message = "INTERCEPTED ERROR : " + message;
}

void warningInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
     intercepted_message = "INTERCEPTED WARNING : " + message;
}

void infoInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
     intercepted_message = "INTERCEPTED INFO : " + message;
}

void debugInterceptor_1(Logger::LogLevel level, const std::string& message, void* userData)
{
   intercepted_message = "INTERCEPTED DEBUG #1 : " + message;
}

void debugInterceptor_2(Logger::LogLevel level, const std::string& message, void* userData)
{
     intercepted_message = "INTERCEPTED DEBUG #2 : " + message;
}

void fatalInterceptor(Logger::LogLevel level, const std::string& message, void* userData)
{
     intercepted_message = "INTERCEPTED FATAL : " + message;
}
// Test Case : Check registration and unregistration of Interceptor
TEST(TEST_LOG_INTERCEPTOR, REGISTER_UNREGISTER)
{
    // Logger #1
    Logger log1("LogInterceptor1");
    log1.setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1.registerInterceptor(level1, debugInterceptor_1, nullptr));
    
    log1.debug("Testing REGISTR_UNREGISTER");
    usleep(500);
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : Testing REGISTR_UNREGISTER");
    
    EXPECT_TRUE(log1.unregisterInterceptor(level1, debugInterceptor_1));
}


// Test Case : Check registration with null callback
TEST(TEST_LOG_INTERCEPTOR, REGISTER_NULL_CALLBACK)
{
    // Logger #1
    Logger log1("LogInterceptor1");
    log1.setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    log1.debug("Register NULL Callback");
    EXPECT_FALSE(log1.registerInterceptor(level1, nullptr, nullptr)); // Interceptor is not registered with null callback
}

// Test Case: Unregister Non-Registered Interceptor
TEST(TEST_LOG_INTERCEPTOR, UNREGISTER_NON_REGISTERED)
{
    Logger log1("LogInterceptor1");
    log1.setMinLevel("debug");

    Logger::LogLevel level = Logger::LogLevel::DEBUG; 
    EXPECT_FALSE(log1.unregisterInterceptor(level, debugInterceptor_1));  // Trying to unregister before it's registered
}

// Test Case: Multiple Interceptors for the Same Log Level
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_INTERCEPTORS_SAME_LEVEL)
{
    Logger log1("LogInterceptor1");
    log1.setMinLevel("debug");

    Logger::LogLevel level = Logger::LogLevel::DEBUG; 
    EXPECT_TRUE(log1.registerInterceptor(level, debugInterceptor_1, nullptr));
    EXPECT_TRUE(log1.registerInterceptor(level, debugInterceptor_2, nullptr));
    
    log1.debug("Multiple interceptors test");
    usleep(500);

    ASSERT_TRUE(intercepted_message.find("INTERCEPTED DEBUG #1 : Multiple interceptors test") != std::string::npos || 
                intercepted_message.find("INTERCEPTED DEBUG #2 : Multiple interceptors test") != std::string::npos);

    EXPECT_TRUE(log1.unregisterInterceptor(level, debugInterceptor_1));
    EXPECT_TRUE(log1.unregisterInterceptor(level, debugInterceptor_2));
}

// Test Case : Check multiple registration for same log level
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_REGISTER)
{
    // Logger #1
    Logger log1("LogInterceptor1");
    log1.setMinLevel("debug");
    usleep(500);
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1.registerInterceptor(level1, debugInterceptor_1, nullptr));
    
    log1.debug("Register Debug Logger");
    usleep(500);
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : Register Debug Logger");
    
    EXPECT_TRUE(log1.unregisterInterceptor(level1, debugInterceptor_1));


    // Logger #2  
    Logger log2("LogInterceptor2");
    log2.setMinLevel("debug");
    Logger::LogLevel level2 = Logger::LogLevel::DEBUG; 
    
    
    EXPECT_TRUE(log2.registerInterceptor(level2, debugInterceptor_2, nullptr));
    
    log2.debug("Register Debug Logger");
    usleep(500);
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #2 : Register Debug Logger");
    
    EXPECT_TRUE(log2.unregisterInterceptor(level2, debugInterceptor_2));
  
}

// Test Case : Check multiple unregister 
TEST(TEST_LOG_INTERCEPTOR, MULTIPLE_UNREGISTER)
{
    // Logger #1
    Logger log1("LogInterceptor1");
    log1.setMinLevel("debug");
    Logger::LogLevel level1 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log1.registerInterceptor(level1, debugInterceptor_1, nullptr));
    
    log1.debug("Testing First UNREGISTER");
    usleep(500);
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : Testing First UNREGISTER");
    
    EXPECT_TRUE(log1.unregisterInterceptor(level1, debugInterceptor_1));
    EXPECT_FALSE(log1.unregisterInterceptor(level1, debugInterceptor_1)); // return false because interceptor already unregistered
    
    log1.debug("Testing Second UNREGISTER");
    usleep(500);
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : Testing First UNREGISTER"); // No new message is intercepted after unregister
}

// Test Case : Check registration and unregistration of Interceptor for all the supported log levels
TEST(TEST_LOG_INTERCEPTOR, ALL_LOG_LEVELS)
{
    // Logger #1
    Logger log1("LogInterceptor1");
    log1.setMinLevel("error");
    Logger::LogLevel level1 = Logger::LogLevel::ERROR; 
    
    EXPECT_TRUE(log1.registerInterceptor(level1, errorInterceptor, nullptr));
    
    log1.error("Testing error interceptor");
    usleep(500);
    ASSERT_EQ(intercepted_message, "INTERCEPTED ERROR : Testing error interceptor");
    
    EXPECT_TRUE(log1.unregisterInterceptor(level1, errorInterceptor));

    // Logger #2
    Logger log2("LogInterceptor2");
    log2.setMinLevel("warning");
    Logger::LogLevel level2 = Logger::LogLevel::WARNING; 
    
    EXPECT_TRUE(log2.registerInterceptor(level2, warningInterceptor, nullptr));
    
    log2.warn("Testing warning interceptor");
    usleep(500);
    ASSERT_EQ(intercepted_message, "INTERCEPTED WARNING : Testing warning interceptor");
    
    EXPECT_TRUE(log2.unregisterInterceptor(level2, warningInterceptor));

    // Logger #3
    Logger log3("LogInterceptor3");
    log3.setMinLevel("info");
    Logger::LogLevel level3 = Logger::LogLevel::INFO; 
    
    EXPECT_TRUE(log3.registerInterceptor(level3, infoInterceptor, nullptr));
    
    log3.info("Testing info interceptor");
    usleep(500);
    ASSERT_EQ(intercepted_message, "INTERCEPTED INFO : Testing info interceptor");
    
    EXPECT_TRUE(log3.unregisterInterceptor(level3, infoInterceptor));

    // Logger #4
    Logger log4("LogInterceptor4");
    log4.setMinLevel("debug");
    Logger::LogLevel level4 = Logger::LogLevel::DEBUG; 
    
    EXPECT_TRUE(log4.registerInterceptor(level4, debugInterceptor_1, nullptr));
    
    log4.debug("Testing debug interceptor");
    usleep(500);
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : Testing debug interceptor");
    
    EXPECT_TRUE(log4.unregisterInterceptor(level4, debugInterceptor_1));

    // Logger #4
    Logger log5("LogInterceptor5");
    log5.setMinLevel("debug");
    Logger::LogLevel level5 = Logger::LogLevel::FATAL; 
    
    EXPECT_TRUE(log5.registerInterceptor(level5, fatalInterceptor, nullptr));
    
    log5.fatal("Testing fatal interceptor");
    usleep(500);
    ASSERT_EQ(intercepted_message, "INTERCEPTED FATAL : Testing fatal interceptor");
    
    EXPECT_TRUE(log5.unregisterInterceptor(level5, fatalInterceptor));

}



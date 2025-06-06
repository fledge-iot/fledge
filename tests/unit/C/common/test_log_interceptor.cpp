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
#include <map>
#include <string>
#include <vector>

using namespace std;

std::string intercepted_message;
Logger* logger = Logger::getLogger();

const char* logLevelToString(Logger::LogLevel level) {
    switch (level) {
        case Logger::LogLevel::ERROR:   return "ERROR";
        case Logger::LogLevel::WARNING: return "WARNING";
        case Logger::LogLevel::INFO:    return "INFO";
        case Logger::LogLevel::DEBUG:   return "DEBUG";
        case Logger::LogLevel::FATAL:   return "FATAL";
        default:                        return "UNKNOWN";
    }
}


enum InterceptType { ERROR, WARNING, INFO, DEBUG1, DEBUG2, FATAL };

// Shared sync control
struct InterceptControl {
    std::mutex mtx;
    std::condition_variable cv;
    bool triggered = false;
};

std::map<InterceptType, InterceptControl> interceptControls;

// Utilities
void signalInterceptor(InterceptType type, const std::string& label, const std::string& message) {
    intercepted_message = "INTERCEPTED " + label + " : " + message;
    InterceptControl& ctrl = interceptControls[type];
    {
        std::lock_guard<std::mutex> lk(ctrl.mtx);
        ctrl.triggered = true;
    }
    ctrl.cv.notify_one();
}

void waitForInterceptor(InterceptType type) {
    InterceptControl& ctrl = interceptControls[type];
    std::unique_lock<std::mutex> lk(ctrl.mtx);
    ctrl.cv.wait(lk, [&ctrl] { return ctrl.triggered; });
    ctrl.triggered = false;
}

// Interceptor functions
void interceptor_ERROR(Logger::LogLevel, const std::string& msg, void*) {
    signalInterceptor(ERROR, "ERROR", msg);
}
void interceptor_WARNING(Logger::LogLevel, const std::string& msg, void*) {
    signalInterceptor(WARNING, "WARNING", msg);
}
void interceptor_INFO(Logger::LogLevel, const std::string& msg, void*) {
    signalInterceptor(INFO, "INFO", msg);
}
void interceptor_DEBUG1(Logger::LogLevel, const std::string& msg, void*) {
    signalInterceptor(DEBUG1, "DEBUG #1", msg);
}
void interceptor_DEBUG2(Logger::LogLevel, const std::string& msg, void*) {
    signalInterceptor(DEBUG2, "DEBUG #2", msg);
}
void interceptor_FATAL(Logger::LogLevel, const std::string& msg, void*) {
    signalInterceptor(FATAL, "FATAL", msg);
}

// ===========================
// Test Cases
// ===========================

// Test Case : Check registration and unregistration of Interceptor
TEST(LOG_INTERCEPTOR_TEST, RegisterUnregister) {
    logger->setMinLevel("debug");
    EXPECT_TRUE(logger->registerInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG1, nullptr));

    logger->debug("Testing REGISTER_UNREGISTER");
    waitForInterceptor(DEBUG1);
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing REGISTER_UNREGISTER");

    EXPECT_TRUE(logger->unregisterInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG1));
}

// Test Case : Check registration with null callback
TEST(LOG_INTERCEPTOR_TEST, RegisterNullCallback) {
    logger->setMinLevel("debug");
    // Interceptor is not registered with null callback
    EXPECT_FALSE(logger->registerInterceptor(Logger::LogLevel::DEBUG, nullptr, nullptr));
}

// Test Case: Unregister Non-Registered Interceptor
TEST(LOG_INTERCEPTOR_TEST, UnregisterNonRegistered) {
    logger->setMinLevel("debug");
    // Trying to unregister before it's registered
    EXPECT_FALSE(logger->unregisterInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG1));
}

// Test Case: Multiple Interceptors for the Same Log Level
TEST(LOG_INTERCEPTOR_TEST, MultipleInterceptorsSameLevel) {
    logger->setMinLevel("debug");

    EXPECT_TRUE(logger->registerInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG1, nullptr));
    EXPECT_TRUE(logger->registerInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG2, nullptr));

    logger->debug("Multiple interceptors test");

    waitForInterceptor(DEBUG1);
    waitForInterceptor(DEBUG2);

    EXPECT_TRUE(intercepted_message.find("DEBUG: Multiple interceptors test") != std::string::npos);

    EXPECT_TRUE(logger->unregisterInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG1));
    EXPECT_TRUE(logger->unregisterInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG2));
}

// Test Case : Check multiple registration for same log level
TEST(LOG_INTERCEPTOR_TEST, MultipleRegister) {
    logger->setMinLevel("debug");

    EXPECT_TRUE(logger->registerInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG1, nullptr));
    logger->debug("Register Debug Logger");
    waitForInterceptor(DEBUG1);
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Register Debug Logger");
    EXPECT_TRUE(logger->unregisterInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG1));

    EXPECT_TRUE(logger->registerInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG2, nullptr));
    logger->debug("Register Debug Logger");
    waitForInterceptor(DEBUG2);
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #2 : DEBUG: Register Debug Logger");
    EXPECT_TRUE(logger->unregisterInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG2));
}

// Test Case : Check multiple unregister 
TEST(LOG_INTERCEPTOR_TEST, MultipleUnregister) {
    logger->setMinLevel("debug");
    EXPECT_TRUE(logger->registerInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG1, nullptr));

    logger->debug("Testing First UNREGISTER");
    waitForInterceptor(DEBUG1);
    ASSERT_EQ(intercepted_message, "INTERCEPTED DEBUG #1 : DEBUG: Testing First UNREGISTER");

    EXPECT_TRUE(logger->unregisterInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG1));
    
    // return false because interceptor already unregistered
    EXPECT_FALSE(logger->unregisterInterceptor(Logger::LogLevel::DEBUG, interceptor_DEBUG1));
}

// Test Case : Check registration and unregistration of Interceptor for all the supported log levels
TEST(LOG_INTERCEPTOR_TEST, AllLogLevels) {
    struct Case {
        Logger::LogLevel level;
        InterceptType type;
        const char* label;
        const char* msg;
        Logger::LogInterceptor callback;

        Case(Logger::LogLevel l, InterceptType t, const char* lbl, const char* m, Logger::LogInterceptor cb)
        : level(l), type(t), label(lbl), msg(m), callback(cb) {}
    };

    std::vector<Case> tests;
    tests.push_back(Case(Logger::LogLevel::ERROR,   ERROR,  "ERROR",   "Testing error interceptor",  interceptor_ERROR));
    tests.push_back(Case(Logger::LogLevel::WARNING, WARNING, "WARNING", "Testing warning interceptor", interceptor_WARNING));
    tests.push_back(Case(Logger::LogLevel::INFO,    INFO,    "INFO",    "Testing info interceptor",   interceptor_INFO));
    tests.push_back(Case(Logger::LogLevel::DEBUG,   DEBUG1,  "DEBUG #1","Testing debug interceptor",  interceptor_DEBUG1));
    tests.push_back(Case(Logger::LogLevel::FATAL,   FATAL,   "FATAL",   "Testing fatal interceptor",  interceptor_FATAL));

    logger->setMinLevel("debug");

    for (size_t i = 0; i < tests.size(); ++i) {
        const Case& test = tests[i];
        EXPECT_TRUE(logger->registerInterceptor(test.level, test.callback, nullptr));

        // Dispatch the appropriate logger function manually
        switch (test.level) {
            case Logger::LogLevel::ERROR:
                logger->error(test.msg);
                break;
            case Logger::LogLevel::WARNING:
                logger->warn(test.msg);
                break;
            case Logger::LogLevel::INFO:
                logger->info(test.msg);
                break;
            case Logger::LogLevel::DEBUG:
                logger->debug(test.msg);
                break;
            case Logger::LogLevel::FATAL:
                logger->fatal(test.msg);
                break;
            default:
                FAIL() << "Unknown log level!";
        }

        waitForInterceptor(test.type);
        std::string expected = std::string("INTERCEPTED ") + test.label + " : " + logLevelToString(test.level) + ": " + test.msg;
        ASSERT_EQ(intercepted_message, expected);

        EXPECT_TRUE(logger->unregisterInterceptor(test.level, test.callback));
    }
}


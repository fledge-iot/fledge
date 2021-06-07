/*
 * Fledge Statistics History
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <purge_system.h>
#include <logger.h>

#include <thread>
#include <csignal>

using namespace std;

volatile std::sig_atomic_t signalReceived = 0;

/**
 * Handle Signals
 */
static void signalHandler(int signal)
{
	signalReceived = signal;
}

/**
 * Constructor for Statistics history task
 */
PurgeSystem::PurgeSystem(int argc, char** argv) : FledgeProcess(argc, argv)
{

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->info("PurgeSystem starting");
	Logger::getLogger()->setMinLevel("warning");
}

/**
 * PurgeSystem class methods
 */
PurgeSystem::~PurgeSystem()
{
	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->info("PurgeSystem end");
	Logger::getLogger()->setMinLevel("warning");
}

/**
 * PurgeSystem run method, called by the base class
 * to start the process and do the actual work.
 */
void PurgeSystem::run() const
{
	// We handle these signals, add more if needed
	std::signal(SIGINT,  signalHandler);
	std::signal(SIGSTOP, signalHandler);
	std::signal(SIGTERM, signalHandler);

	// FIXME_I:
	std::this_thread::sleep_for(std::chrono::milliseconds(150));

	processEnd();
}

/**
 * Process a single statistics key
 *
 * @param key	The statistics key to process
 */
void PurgeSystem::processEnd() const
{
	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->info("PurgeSystem end");
	Logger::getLogger()->setMinLevel("warning");
}

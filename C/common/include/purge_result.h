#ifndef _PURGE_RESULT_H
#define _PURGE_RESULT_H
/*
 * FogLAMP storage client.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>
#include <string.h>
#include <sstream>
#include <iostream>
#include <reading.h>
#include <rapidjson/document.h>
#include <vector>

/**
 */
class PurgeResult {
	public:
		PurgeResult(const std::string& json);
		const unsigned long	getRemoved() const { return m_removed; };
		const unsigned long	getUnsentPurged() const { return m_unsentPurged; };
		const unsigned long	getUnsentRetained() const { return m_unsentRetained; };
		const unsigned long	getRemaining() const { return m_remaining; };
	private:
		unsigned long 	m_removed;
		unsigned long 	m_unsentPurged;
		unsigned long 	m_unsentRetained;
		unsigned long 	m_remaining;

};

#endif

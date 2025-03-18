#ifndef _PIPELINE_DEBUGGER_H
#define _PIPELINE_DEBUGGER_H
/*
 * Fledge filter pipeline debugger.
 *
 * Copyright (c) 2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <reading_set.h>
#include <reading.h>
#include <reading_circularbuffer.h>
#include <mutex>
#include <vector>
#include <memory>

/**
 * The debugger class for elements in a pipeline
 */
class PipelineDebugger {
	public:
		PipelineDebugger();
		~PipelineDebugger();
		typedef enum debuggerActions
		{
			NoAction,
			Block
		} DebuggerActions;
		DebuggerActions		process(ReadingSet *readingSet);
		void			setBuffer(unsigned int size);
		void			clearBuffer();
		std::vector<std::shared_ptr<Reading>>
					fetchBuffer();
	private:
		ReadingCircularBuffer	*m_buffer;
		std::mutex		m_bufferMutex;

};

#endif

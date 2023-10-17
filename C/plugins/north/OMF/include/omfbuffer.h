#ifndef _OMF_BUFFER_H
#define _OMF_BUFFER_H
/*
 * Fledge OMF North plugin buffer class
 *
 * Copyright (c) 2023 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <string>
#include <list>

#define BUFFER_CHUNK	8192

/**
 * Buffer class designed to hold OMF payloads that can
 * grow as required but have minimal copy semantics.
 *
 * TODO Add a coalesce and compress public entry point
 */
class OMFBuffer {
	class Buffer {
		public:
			Buffer();
			Buffer(unsigned int);
			~Buffer();
			char		*detach();
			char		*data;
			unsigned int	offset;
			unsigned int	length;
			bool		attached;
	};

        public:
                OMFBuffer();
                ~OMFBuffer();

		bool			isEmpty() { return buffers.empty() || (buffers.size() == 1 && buffers.front()->offset == 0); }
		void			append(const char);
		void			append(const char *);
		void			append(const int);
		void			append(const unsigned int);
		void			append(const long);
		void			append(const unsigned long);
		void			append(const double);
		void			append(const std::string&);
		void			quote(const std::string&);
		const char		*coalesce();
		void			clear();

	private:
		std::list<Buffer *>	buffers;
};

#endif

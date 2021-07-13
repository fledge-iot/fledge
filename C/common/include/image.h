#ifndef _IMAGE_H
#define _IMAGE_H
/*
 * Fledge
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

/**
 * Base Image class that will be used within data points to store image data
 */
class Image {
	public:
		Image(int width, int height, int depth, void *data);
		Image(const Image& rhs);
		Image& operator=(const Image& rhs);
		~Image();
		int		getHeight() { return m_height; };
		int		getWidth() { return m_width; };
		int		getDepth() { return m_depth; };
	private:
		int		m_width;
		int		m_height;
		int		m_depth;
		void		*m_pixels;
};

#endif

#ifndef _DPIMAGE_H
#define _DPIMAGE_H
/*
 * Fledge
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

/**
 * Base Image class that will be used within data points to store image data
 */
class DPImage {
	public:
		DPImage(int width, int height, int depth, void *data);
		DPImage(const DPImage& rhs);
		DPImage& operator=(const DPImage& rhs);
		~DPImage();
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

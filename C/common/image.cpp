/*
 * Fledge DPImage class 
 *
 * Copyright (c) 2020 Dianomic System
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <dpimage.h>
#include <logger.h>
#include <string.h>
#include <exception>
#include <stdexcept>

using namespace std;

/**
 * DPImage constructor
 *
 * @param width		The image width
 * @param height	The image height
 * @param depth		The image depth
 * @param data		The actual image data
 */
DPImage::DPImage(int width, int height, int depth, void *data) : m_width(width),
	m_height(height), m_depth(depth)
{
	m_byteSize = width * height * (depth / 8);
	m_pixels = (void *)malloc(m_byteSize);
	if (m_pixels)
	{
		memcpy(m_pixels, data, m_byteSize);
	}
	else
	{
		throw runtime_error("Insufficient memory to store image");
	}
}

/**
 * Copy constructor
 *
 * @param DPImage		The image to copy
 */
DPImage::DPImage(const DPImage& rhs)
{
	m_width = rhs.m_width;
	m_height = rhs.m_height;
	m_depth = rhs.m_depth;

	m_byteSize = m_width * m_height * (m_depth / 8);
	m_pixels = (void *)malloc(m_byteSize);
	if (m_pixels)
	{
		memcpy(m_pixels, rhs.m_pixels, m_byteSize);
	}
	else
	{
		throw runtime_error("Insufficient memory to store image");
	}
}

/**
 * Assignment operator
 * @param rhs	Righthand side of equals operator
 */
DPImage& DPImage::operator=(const DPImage& rhs)
{
	// Free any old data
	if (m_pixels)
		free(m_pixels);
    
	m_width = rhs.m_width;
	m_height = rhs.m_height;
	m_depth = rhs.m_depth;

	m_byteSize = m_width * m_height * (m_depth / 8);
	m_pixels = (void *)malloc(m_byteSize);
	if (m_pixels)
	{
		memcpy(m_pixels, rhs.m_pixels, m_byteSize);
	}
	else
	{
		throw runtime_error("Insufficient memory to store image");
	}
	return *this;
}

/**
 * Destructor for the image
 */
DPImage::~DPImage()
{
	if (m_pixels)
		free(m_pixels);
	m_pixels = NULL;
}

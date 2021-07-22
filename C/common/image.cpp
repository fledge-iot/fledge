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
	// TODO deal with the data
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

	// TODO deal with data
}

/**
 * Assignment operator
 * @param rhs	Righthand side of equals operator
 */
DPImage& DPImage::operator=(const DPImage& rhs)
{
	// Free any old data

	m_width = rhs.m_width;
	m_height = rhs.m_height;
	m_depth = rhs.m_depth;

	// TODO deal with data
}

/**
 * Destructor for the image
 */
DPImage::~DPImage()
{
}

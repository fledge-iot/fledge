#ifndef _UPDATE_MODIFIER_H
#define _UPDATE_MODIFIER_H
/*
 * Fledge storage client.
 *
 * Copyright (c) 2022 Dianonic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>


/**
 * Update modifier
 */
class UpdateModifier {
	public:
		UpdateModifier(const std::string& modifier) :
				m_modifier(modifier)
		{
		};
		~UpdateModifier();
		const std::string	toJSON() const { return m_modifier; };
	private:
		UpdateModifier(const UpdateModifier&);
		UpdateModifier&		operator=(UpdateModifier const&);
		const std::string	m_modifier;
};
#endif


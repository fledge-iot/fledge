#ifndef _JSON_PROPERTIES_H
#define _JSON_PROPERTIES_H
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
#include <sstream>
#include <iostream>
#include <vector>

class JSONProperty {
	public:
		JSONProperty(const std::string& column, std::vector<std::string> path, const std::string& value) :
					m_column(column), m_value(value)
		{
			for (std::vector<std::string>::const_iterator it = path.cbegin();
					it != path.cend(); ++it)
				m_path.push_back(*it);
		}

		const std::string	toJSON() const
		{
		std::ostringstream json;

			json << "{ \"column\" : \"" << m_column << "\",";
			json << " \"path\" : [";
			for (std::vector<std::string>::const_iterator it = m_path.cbegin();
					it != m_path.cend(); ++it)
			{
				json << "\"" << *it << "\"";
				if ((it + 1) != m_path.cend())
					json << ",";
			}
			json << "],";
			json << "\"value\" : \"" << m_value << "\" }";
			return json.str();
		}
	private:
		const std::string		m_column;
		const std::string		m_value;
		std::vector<std::string>	m_path;
};

/**
 * Class that defines JSON properties for update
 */
class JSONProperties : public std::vector<JSONProperty>
{
	public:
		const std::string	toJSON() const
		{
		std::ostringstream json;

			json << "\"json_properties\" : [ ";
			for (std::vector<JSONProperty>::const_iterator it = this->cbegin();
				 it != this->cend(); ++it)

			{
				json << it->toJSON();
				if (it + 1 != this->cend())
					json << ", ";
				else
					json << " ";
			}
			json << "]";
			return json.str();
		};
};
#endif


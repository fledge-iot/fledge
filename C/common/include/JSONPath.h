/*
 * Fledge RapaidJSON JSONPath search helper
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#ifndef _JSONPATH_H
#define _JSONPATH_H

#include <rapidjson/document.h>
#include <string>
#include <vector>
#include <logger.h>

/**
 * A simple implementation of a JSON Path search mechanism to use
 * alongside RapidJSON
 */
class JSONPath {
	public:
		JSONPath(const std::string& path);
		~JSONPath();
		rapidjson::Value *findNode(rapidjson::Value& root);
	private:
		class PathComponent {
			public:
				virtual rapidjson::Value *match(rapidjson::Value *node) = 0;
		};
		class LiteralPathComponent : public PathComponent {
			public:
				LiteralPathComponent(std::string& name);
				rapidjson::Value *match(rapidjson::Value *node);
			private:
				std::string	m_name;
		};
		class IndexPathComponent : public PathComponent {
			public:
				IndexPathComponent(std::string& name, int index);
				rapidjson::Value *match(rapidjson::Value *node);
			private:
				std::string	m_name;
				int		m_index;
		};
		class MatchPathComponent : public PathComponent {
			public:
				MatchPathComponent(std::string& name, std::string& property, std::string& value);
				rapidjson::Value *match(rapidjson::Value *node);
			private:
				std::string	m_name;
				std::string	m_property;
				std::string	m_value;
		};
		void		parse();
		std::string	m_path;
		std::vector<PathComponent *>
				m_parsed;
		Logger		*m_logger;
};

#endif

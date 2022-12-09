#ifndef _BASETYPES_H
#define _BASETYPES_H
/*
 * Fledge OSIsoft OMF interface to PI Server.
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <plugin_api.h>

static const char *baseOMFTypes = QUOTE(
		[
   {
      "id":"Double",
      "type":"object",
      "classification":"dynamic",
      "properties":{
         "Double":{
            "type":["number", "null"],
            "format":"float64"
         },
         "Time":{
            "type":"string",
            "format":"date-time",
            "isindex":true
         }
      }
   },
   {
      "id":"Integer32",
      "type":"object",
      "classification":"dynamic",
      "properties":{
         "Integer32":{
            "type":["integer","null"],
            "format":"int32",
         },
         "Time":{
            "type":"string",
            "format":"date-time",
            "isindex":true
         }
      }
   },
   {
      "id":"Integer64",
      "type":"object",
      "classification":"dynamic",
      "properties":{
         "Integer64":{
            "type":["integer","null"],
            "format":"int64",
         },
         "Time":{
            "type":"string",
            "format":"date-time",
            "isindex":true
         }
      }
   },
   {
      "id":"String",
      "type":"object",
      "classification":"dynamic",
      "properties":{
         "String":{
            "type":["string","null"]
         },
         "Time":{
            "type":"string",
            "format":"date-time",
            "isindex":true
         }
      }
   },
   {
      "id":"FledgeAsset",
      "type":"object",
      "classification":"static",
      "properties":{
         "AssetId": {"type": "string", "isindex": true },
	  "Name" : { "type": "string", "isname": true }
      }

   }
]);

#endif

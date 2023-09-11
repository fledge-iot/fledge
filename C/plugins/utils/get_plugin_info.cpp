/*
 * Utility to extract plugin_info from north/south C plugin library
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <dlfcn.h>
#include <syslog.h>
#include "plugin_api.h"

typedef PLUGIN_INFORMATION *(*func_t)();

/**
 * Extract value of a given symbol from given plugin library
 *
 *    Usage: get_plugin_info <plugin library> <function symbol to fetch plugin info from>
 *
 * @param argv[1]  relative/absolute path to north/south C plugin shared library
 *
 * @param argv[2]  symbol to extract value from (defaults 'plugin_info')
 */
int main(int argc, char *argv[])
{
  void *hndl;
  char *routine = (char *)"plugin_info";

  if (argc == 3)
  {
	  routine = argv[2];
  }
  else if (argc < 2)
  {
    fprintf(stderr, "Insufficient number of args...\n\nUsage: %s <plugin library> [ <function to fetch plugin info> ]\n", argv[0]);
    exit(1);
  }

  openlog("Fledge PluginInfo", LOG_PID|LOG_CONS, LOG_USER);
  setlogmask(LOG_UPTO(LOG_WARNING));

  if (access(argv[1], F_OK|R_OK) != 0)
  {
    syslog(LOG_ERR, "Unable to access library file '%s', exiting...\n", argv[1]);
    exit(2);
  }


  if ((hndl = dlopen(argv[1], RTLD_GLOBAL|RTLD_LAZY)) != NULL)
  {
    func_t infoEntry = (func_t)dlsym(hndl, routine);
    if (infoEntry == NULL)
    {
      // Unable to find plugin_info entry point
      syslog(LOG_ERR, "Plugin library %s does not support %s function : %s\n", argv[1], routine, dlerror());
      dlclose(hndl);
      closelog();
      exit(3);
    }
    PLUGIN_INFORMATION *info = (PLUGIN_INFORMATION *)(*infoEntry)();
    printf("{\"name\": \"%s\", \"version\": \"%s\", \"type\": \"%s\", \"interface\": \"%s\", \"flag\": %d, \"config\": %s}\n", info->name, info->version, info->type, info->interface, info->options, info->config);
  }
  else
  {
    syslog(LOG_ERR, "dlopen failed: %s\n", dlerror());
  }
  closelog();
  
  return 0;
}


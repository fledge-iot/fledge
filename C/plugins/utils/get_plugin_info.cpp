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
#include "plugin_api.h"

typedef PLUGIN_INFORMATION *(*func_t)();

/**
 * Extract value of a given symbol from given plugin library
 *
 *    Usage: get_plugin_info <plugin library> <function symbol to fetch plugin info from>
 *
 * @param argv[1]  relative/absolute path to north/south C plugin shared library
 *
 * @param argv[2]  symbol to extract value from (typically 'plugin_info')
 */
int main(int argc, char *argv[])
{
  void *hndl;

  if (argc<2)
  {
    fprintf(stderr, "Insufficient number of args...\n\nUsage: %s <plugin library> <function to fetch plugin info>\n", argv[0]);
    exit(1);
  }

  if (access(argv[1], F_OK|R_OK) != 0)
  {
    fprintf(stderr, "Unable to access library file '%s', exiting...\n", argv[1]);
    exit(2);
  }

  if ((hndl = dlopen(argv[1], RTLD_GLOBAL|RTLD_LAZY)) != NULL)
  {
    func_t infoEntry = (func_t)dlsym(hndl, argv[2]);
    if (infoEntry == NULL)
    {
      // Unable to find plugin_info entry point
      fprintf(stderr, "Plugin library %s does not support %s function : %s\n", argv[1], argv[2], dlerror());
      dlclose(hndl);
      exit(3);
    }
    PLUGIN_INFORMATION *info = (PLUGIN_INFORMATION *)(*infoEntry)();
    printf("%s\n", info->config);
  }
  else
  {
    fprintf(stderr, "dlopen failed: %s\n", dlerror());
  }

  return 0;
}


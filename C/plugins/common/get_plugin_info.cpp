#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <dlfcn.h>
#include "plugin_api.h"

typedef PLUGIN_INFORMATION *(*func_t)();

int main(int argc, char *argv[])
{
  void *hndl;

  if (argc<2)
  {
    printf("Insufficient number of args...\n\nUsage: %s <plugin library> <function to fetch plugin info>\n", argv[0]);
    exit(1);
  }
  //printf("Library: '%s' , Symbol: '%s' \n ", argv[1], argv[2]);

  if (access(argv[1], F_OK) != 0)
  {
    printf("Unable to access library file '%s', exiting...\n", argv[1]);
    exit(2);
  }

  if ((hndl = dlopen(argv[1], RTLD_GLOBAL|RTLD_LAZY)) != NULL)
  {
    func_t infoEntry = (func_t)dlsym(hndl, argv[2]);
    if (infoEntry == NULL)
    {
      // Unable to find plugin_info entry point
      printf("Plugin library %s does not support %s function : %s\n", argv[1], argv[2], dlerror());
      dlclose(hndl);
      exit(3);
    }
    PLUGIN_INFORMATION *info = (PLUGIN_INFORMATION *)(*infoEntry)();
    printf("Returned value (%s): '%s'\n", argv[2], info->config);
  }
  else
  {
    printf("dlopen failed: %s\n", dlerror());
  }

  return 0;
}


#include <storage_api.h>

int main(int argc, char *argv[])
{
	StorageApi *api = new StorageApi(8080, 1);
  api->initResources();
	api->start();

	api->wait();
  return 0;
}

#include <connection_manager.h>
#include <connection.h>


ConnectionManager *ConnectionManager::instance = 0;


ConnectionManager::ConnectionManager()
{
}

ConnectionManager *ConnectionManager::getInstance()
{
  if (instance == 0)
  {
    instance = new ConnectionManager();
  }
  return instance;
}

void ConnectionManager::growPool(unsigned int delta)
{
  while (delta-- > 0)
  {
    Connection *conn = new Connection();
    idleLock.lock();
    idle.push_back(conn);
    idleLock.unlock();
  }
}

unsigned int ConnectionManager::shrinkPool(unsigned int delta)
{
unsigned int removed = 0;
Connection   *conn;

  while (delta-- > 0)
  {
    idleLock.lock();
    conn = idle.back();
    idle.pop_back();
    idleLock.unlock();
    if (conn)
    {
      delete conn;
      removed++;
    }
    else
    {
      break;
    }
  }
  return removed;
}

Connection *ConnectionManager::allocate()
{
Connection *conn = 0;

    idleLock.lock();
    conn = idle.front();
    idle.pop_front();
    idleLock.unlock();
    if (conn)
    {
      inUseLock.lock();
      inUse.push_front(conn);
      inUseLock.unlock();
    }
    return conn;
}

void ConnectionManager::release(Connection *conn)
{
  inUseLock.lock();
  inUse.remove(conn);
  inUseLock.unlock();
  idleLock.lock();
  idle.push_back(conn);
  idleLock.unlock();
}


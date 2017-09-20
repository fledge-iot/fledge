#ifndef _CONNECTION_MANAGER_H
#define _CONNECTION_MANAGER_H

#include <list>
#include <mutex>

class Connection;

/**
 * Singleton class to manage Postgres connection pool
 */
class ConnectionManager {
  public:
    static ConnectionManager  *getInstance();
    void                      growPool(unsigned int);
    unsigned int              shrinkPool(unsigned int);
    Connection                *allocate();
    void                      release(Connection *);

  private:
    ConnectionManager();
    static ConnectionManager     *instance;
    std::list<Connection *>      idle;
    std::list<Connection *>      inUse;
    std::mutex                   idleLock;
    std::mutex                   inUseLock;
};

#endif

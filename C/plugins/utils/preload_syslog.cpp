/*
 * Utility to extract plugin_info from north/south C plugin library
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Ashwini Kumar Pandey
 */
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <iostream>
#include <mutex>
#include <cstdlib>
#include <dlfcn.h>
#include <cstdarg>
#include <sys/un.h>
#include <syslog.h>

extern "C" {
typedef ssize_t (*orig_send_type)(int, const void *, size_t, int);
typedef ssize_t (*orig_sendto_type)(int, const void *, size_t, int, const struct sockaddr *, socklen_t);

// Static variables and mutex for UDP socket initialization
static int udpSocket = -1;
static std::mutex socketMutex;

// Helper function to initialize the UDP socket
void initializeUDPSocket() {
    std::lock_guard<std::mutex> lock(socketMutex);
    if (udpSocket == -1) {
        udpSocket = socket(AF_INET, SOCK_DGRAM, 0);
        if (udpSocket < 0) {
            perror("Socket creation failed");
        } else {
            fprintf(stderr, "[INFO] UDP socket initialized successfully\n");
        }
    }
}

// Helper function to check if a socket is connected to /dev/log
bool isDevLog(const struct sockaddr_un* addr) {
    //return addr && addr->sun_family == AF_UNIX && strcmp(addr->sun_path, "/dev/log") == 0;
    return addr && addr->sun_family == AF_UNIX && strcmp(addr->sun_path, "/run/systemd/journal/dev-log") == 0;
}

// Define the original connect function pointer
typedef int (*orig_connect_t)(int, const struct sockaddr*, socklen_t);

int connect(int sockfd, const struct sockaddr* addr, socklen_t addrlen) {
    // Check if the target is `/dev/log`
    fprintf(stderr, "[INFO] Intercepted connect call to /dev/log\n");
    if (addr->sa_family == AF_UNIX) {
        const struct sockaddr_un* un_addr = (const struct sockaddr_un*)addr;
        if (strcmp(un_addr->sun_path, "/dev/log") == 0) {
            fprintf(stderr, "[INFO] Intercepted connect call to /dev/log\n");
            // Custom logic: Redirect or handle the connection
            // Example: Forward the connection to an alternative path
            struct sockaddr_un new_addr = *un_addr;
            strcpy(new_addr.sun_path, "/tmp/log");
            orig_connect_t orig_connect = (orig_connect_t)dlsym(RTLD_NEXT, "connect");
            return orig_connect(sockfd, (const struct sockaddr*)&new_addr, addrlen);
        }
    }

    // Call the original connect function for other cases
    orig_connect_t orig_connect = (orig_connect_t)dlsym(RTLD_NEXT, "connect");
    return orig_connect(sockfd, addr, addrlen);
}

// Helper function to forward data to the UDP socket
ssize_t forwardToUDP(const void* buf, size_t len) {
    initializeUDPSocket();
    if (udpSocket < 0) {
        fprintf(stderr, "[ERROR] UDP socket is not initialized. Cannot forward data to UDP.\n");
        return -1;
    }

    struct sockaddr_in udp_addr;
    udp_addr.sin_family = AF_INET;
    udp_addr.sin_port = htons(5140);
    udp_addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    ssize_t udp_sent = sendto(udpSocket, buf, len, 0, (struct sockaddr*)&udp_addr, sizeof(udp_addr));
    if (udp_sent < 0) {
        perror("[ERROR] Failed to send data to UDP socket");
    } else {
        fprintf(stderr, "[INFO] Data successfully forwarded to UDP socket on port 5140\n");
    }

    return udp_sent;
}

// Intercept send system call
ssize_t send(int sockfd, const void* buf, size_t len, int flags) {
    static orig_send_type orig_send = nullptr;
    if (!orig_send) {
        orig_send = (orig_send_type)dlsym(RTLD_NEXT, "send");
        if (!orig_send) {
            fprintf(stderr, "[ERROR] Failed to resolve original send: %s\n", dlerror());
            return -1;
        }
    }

    fprintf(stderr, "[DEBUG] Intercepting send: sockfd=%d, len=%zu, flags=%d\n", sockfd, len, flags);

    struct sockaddr_un peer_addr;
    socklen_t peer_len = sizeof(peer_addr);

    if (getpeername(sockfd, (struct sockaddr*)&peer_addr, &peer_len) == 0) {
        fprintf(stderr, "[DEBUG] Peer address family: %d\n", peer_addr.sun_family);
        if (isDevLog(&peer_addr)) {
            fprintf(stderr, "[INFO] Intercepted data destined for /dev/log\n");
            return forwardToUDP(buf, len);
        }
    } else {
        perror("[ERROR] getpeername failed");
    }

    return orig_send(sockfd, buf, len, flags);
}

// Intercept sendto system call
ssize_t sendto(int sockfd, const void* buf, size_t len, int flags, const struct sockaddr* dest_addr, socklen_t addrlen) {
    static orig_sendto_type orig_sendto = nullptr;
    fprintf(stderr, "[DEBUG] Intercepting sendto: sockfd=%d, len=%zu, flags=%d\n", sockfd, len, flags);
    if (!orig_sendto) {
        orig_sendto = (orig_sendto_type)dlsym(RTLD_NEXT, "sendto");
        if (!orig_sendto) {
            fprintf(stderr, "[ERROR] Failed to resolve original sendto: %s\n", dlerror());
            return -1;
        }
    }

    fprintf(stderr, "[DEBUG] Intercepting sendto: sockfd=%d, len=%zu, flags=%d\n", sockfd, len, flags);

    if (dest_addr && dest_addr->sa_family == AF_UNIX) {
        const struct sockaddr_un* un_addr = reinterpret_cast<const struct sockaddr_un*>(dest_addr);
        fprintf(stderr, "[DEBUG] Destination address path: %s\n", un_addr->sun_path);
        if (isDevLog(un_addr)) {
            fprintf(stderr, "[INFO] Intercepted sendto data destined for /dev/log\n");
            return forwardToUDP(buf, len);
        }
    }

    return orig_sendto(sockfd, buf, len, flags, dest_addr, addrlen);
}

// Custom syslog function
void syslog(int priority, const char* format, ...) {
    const char* logIpEnv = std::getenv("LOG_IP");
    const char* logPortEnv = std::getenv("LOG_PORT");

    std::string logIp = logIpEnv ? logIpEnv : "127.0.0.1";
    int logPort = logPortEnv ? std::stoi(logPortEnv) : 5140;

    fprintf(stderr, "[DEBUG] syslog called. Priority: %d, Log IP: %s, Log Port: %d\n", priority, logIp.c_str(), logPort);

    initializeUDPSocket();

    va_list args;
    va_start(args, format);
    char buffer[1024];
    vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);

    if (udpSocket != -1) {
        struct sockaddr_in serverAddr;
        serverAddr.sin_family = AF_INET;
        serverAddr.sin_port = htons(logPort);
        inet_pton(AF_INET, logIp.c_str(), &serverAddr.sin_addr);

        sendto(udpSocket, buffer, strlen(buffer), 0, (const struct sockaddr*)&serverAddr, sizeof(serverAddr));
        fprintf(stderr, "[INFO] Log message sent to UDP: %s\n", buffer);
    } else {
        fprintf(stderr, "[ERROR] UDP socket is not initialized. Log message not sent.\n");
    }

    // Call the original syslog function if needed
    typedef void (*orig_syslog_type)(int, const char*, ...);
    static orig_syslog_type orig_syslog = (orig_syslog_type)dlsym(RTLD_NEXT, "syslog");
    if (orig_syslog) {
        va_list args2;
        va_start(args2, format);
        orig_syslog(priority, format, args2);
        va_end(args2);
    }
}
}
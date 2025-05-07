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
 #include <cstdarg>
 #include <sys/un.h>
 #include <syslog.h>
 
 extern "C" {
 
 // Constants
 constexpr int DEFAULT_UDP_PORT = 5140;
 constexpr const char* DEFAULT_UDP_IP = "127.0.0.1";
 constexpr const char* DEV_LOG_PATH = "/run/systemd/journal/dev-log";
 
 // Static variables and mutex for UDP socket initialization
 static int udpSocket = -1;
 static std::mutex socketMutex;
 
 /**
  * @brief Initializes a UDP socket if not already initialized.
  * 
  * This function creates a UDP socket to be used for forwarding log messages
  * to a predefined address and port. It ensures thread-safety using a mutex.
  */
 void initializeUDPSocket() 
 {
     std::lock_guard<std::mutex> lock(socketMutex);
     if (udpSocket == -1) 
     {
         udpSocket = socket(AF_INET, SOCK_DGRAM, 0);
         if (udpSocket < 0) 
         {
             perror("[ERROR] Socket creation failed");
         } 
         else 
         {
             fprintf(stderr, "[INFO] UDP socket initialized successfully\n");
         }
     }
 }
 
 /**
  * @brief Checks if a given address corresponds to the system's /dev/log.
  *
  * @param addr Pointer to the sockaddr_un structure representing the address.
  * @return true if the address matches /dev/log; false otherwise.
  */
 inline bool isDevLog(const struct sockaddr_un* addr) 
 {
     return addr && addr->sun_family == AF_UNIX && strcmp(addr->sun_path, DEV_LOG_PATH) == 0;
 }
 
 /**
  * @brief Forwards log data to a UDP socket.
  *
  * @param buf Pointer to the data buffer to be sent.
  * @param len Length of the data buffer.
  * @return ssize_t Number of bytes sent, or -1 on failure.
  */
 ssize_t forwardToUDP(const void* buf, size_t len) {
     initializeUDPSocket();
     if (udpSocket < 0) 
     {
         fprintf(stderr, "[ERROR] UDP socket is not initialized. Cannot forward data to UDP.\n");
         return -1;
     }
 
     struct sockaddr_in udp_addr {};
     udp_addr.sin_family = AF_INET;
     udp_addr.sin_port = htons(DEFAULT_UDP_PORT);
     udp_addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
 
     ssize_t udp_sent = sendto(udpSocket, buf, len, 0, (struct sockaddr*)&udp_addr, sizeof(udp_addr));
     if (udp_sent < 0) 
     {
         perror("[ERROR] Failed to send data to UDP socket");
     } 
     else
     {
         fprintf(stderr, "[INFO] Data successfully forwarded to UDP socket on port %d\n", DEFAULT_UDP_PORT);
     }
 
     return udp_sent;
 }
 
 /**
  * @brief Intercepts the `send` system call and handles the logic without calling the original function.
  *
  * @param sockfd File descriptor of the socket.
  * @param buf Pointer to the data buffer.
  * @param len Length of the data buffer.
  * @param flags Flags for the send operation.
  * @return ssize_t Number of bytes sent, or -1 on failure.
  */
 ssize_t send(int sockfd, const void* buf, size_t len, int flags) {
     fprintf(stderr, "[DEBUG] Intercepting send: sockfd=%d, len=%zu, flags=%d\n", sockfd, len, flags);
 
     struct sockaddr_un peer_addr {};
     socklen_t peer_len = sizeof(peer_addr);
 
     if (getpeername(sockfd, (struct sockaddr*)&peer_addr, &peer_len) == 0 && isDevLog(&peer_addr)) 
     {
         fprintf(stderr, "[INFO] Intercepted data destined for /dev/log\n");
         return forwardToUDP(buf, len);
     }
 
     fprintf(stderr, "[WARNING] Data not destined for /dev/log. Ignoring send operation.\n");
     return -1; // Indicate that the operation was ignored
 }
 
 /**
  * @brief Intercepts the `sendto` system call and handles the logic without calling the original function.
  *
  * @param sockfd File descriptor of the socket.
  * @param buf Pointer to the data buffer.
  * @param len Length of the data buffer.
  * @param flags Flags for the sendto operation.
  * @param dest_addr Destination address structure.
  * @param addrlen Length of the destination address structure.
  * @return ssize_t Number of bytes sent, or -1 on failure.
  */
 ssize_t sendto(int sockfd, const void* buf, size_t len, int flags, const struct sockaddr* dest_addr, socklen_t addrlen) 
 {
     fprintf(stderr, "[DEBUG] Intercepting sendto: sockfd=%d, len=%zu, flags=%d\n", sockfd, len, flags);
 
     if (dest_addr && dest_addr->sa_family == AF_UNIX) 
     {
         const auto* un_addr = reinterpret_cast<const struct sockaddr_un*>(dest_addr);
         if (isDevLog(un_addr)) 
         {
             fprintf(stderr, "[INFO] Intercepted sendto data destined for /dev/log\n");
             return forwardToUDP(buf, len);
         }
     }
 
     fprintf(stderr, "[WARNING] Data not destined for /dev/log. Ignoring sendto operation.\n");
     return -1; // Indicate that the operation was ignored
 }
 
 /**
  * @brief Custom implementation of syslog that sends log messages to a UDP socket.
  *
  * This function does not call the original syslog implementation.
  *
  * @param priority Priority of the log message.
  * @param format Format string for the log message.
  * @param ... Additional arguments for the format string.
  */
 void syslog(int priority, const char* format, ...) 
 {
     const char* logIpEnv = std::getenv("LOG_IP");
     const char* logPortEnv = std::getenv("LOG_PORT");
 
     std::string logIp = logIpEnv ? logIpEnv : DEFAULT_UDP_IP;
     int logPort = logPortEnv ? std::stoi(logPortEnv) : DEFAULT_UDP_PORT;
 
     fprintf(stderr, "[DEBUG] syslog called. Priority: %d, Log IP: %s, Log Port: %d\n", priority, logIp.c_str(), logPort);
 
     initializeUDPSocket();
 
     va_list args;
     va_start(args, format);
     char buffer[1024];
     vsnprintf(buffer, sizeof(buffer), format, args);
     va_end(args);
 
     if (udpSocket != -1) 
     {
         struct sockaddr_in serverAddr {};
         serverAddr.sin_family = AF_INET;
         serverAddr.sin_port = htons(logPort);
         inet_pton(AF_INET, logIp.c_str(), &serverAddr.sin_addr);
 
         sendto(udpSocket, buffer, strlen(buffer), 0, (const struct sockaddr*)&serverAddr, sizeof(serverAddr));
         fprintf(stderr, "[INFO] Log message sent to UDP: %s\n", buffer);
     } 
     else 
     {
         fprintf(stderr, "[ERROR] UDP socket is not initialized. Log message not sent.\n");
     }
 }
 
 } // extern "C"

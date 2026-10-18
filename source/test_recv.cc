#include "server.hpp"

#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <iostream>

void Check(bool passed, const char *name) {
    if (!passed) {
        std::cerr << "FAIL: " << name << std::endl;
        std::exit(1);
    }
    std::cout << "PASS: " << name << std::endl;
}

int main() {
    int fds[2];
    Check(socketpair(AF_UNIX, SOCK_STREAM, 0, fds) == 0,
          "create socket pair");

    Socket reader(fds[0]);
    Socket writer(fds[1]);
    char buf[16];

    // 对端仍开着，但暂时没有数据
    Check(reader.NonBlockRecv(buf, sizeof(buf)) == 0,
          "no data yet");

    // 先发送数据，再关闭；接收方应先读到已有数据
    Check(writer.Send("abc", 3) == 3, "send data");
    writer.Close();

    Check(reader.NonBlockRecv(buf, sizeof(buf)) == 3,
          "receive buffered data");
    Check(std::memcmp(buf, "abc", 3) == 0,
          "received data matches");

    // 故意留下旧错误，验证 EOF 判断不依赖 errno
    errno = EAGAIN;
    Check(reader.NonBlockRecv(buf, sizeof(buf)) == -1,
          "EOF with stale EAGAIN");

    errno = EINTR;
    Check(reader.NonBlockRecv(buf, sizeof(buf)) == -1,
          "EOF with stale EINTR");

    Check(reader.NonBlockRecv(buf, 0) == 0,
          "zero-length receive");

    reader.Close();
    std::cout << "All receive tests passed" << std::endl;
}
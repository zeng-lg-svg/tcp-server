#include "http.hpp"

int main() {
    HttpServer server(18085);
    server.SetThreadCount(1);

    server.Get("/fixed",
        [](const HttpRequest &, HttpResponse *rsp) {
            rsp->SetContent("hello", "text/plain");
        });

    server.Get("/empty",
        [](const HttpRequest &, HttpResponse *rsp) {
            rsp->SetContent("", "text/plain");
        });

    // 故意提供正文及错误头部，检查发送层是否正确处理
    for (int code : {204, 304, 205}) {
        server.Get("/status/" + std::to_string(code),
            [code](const HttpRequest &, HttpResponse *rsp) {
                rsp->_statu = code;
                rsp->_body = "THIS_BODY_MUST_NOT_BE_SENT";
                rsp->_headers["content-length"] = "999";
                rsp->_headers["transfer-encoding"] = "chunked";
            });
    }

    server.Listen();
    return 0;
}
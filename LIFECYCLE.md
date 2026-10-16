## 独立最小复现

构造延迟任务场景：创建对象、保存任务、释放外部强引用，
最后执行任务。

使用 AddressSanitizer 编译并分别运行两种模式：

- bad：任务捕获裸指针。对象销毁后执行任务，
  ASan 报告 heap-use-after-free。
- good：任务捕获 shared_ptr。对象在任务执行期间保持存活，
  移除任务后析构，本次运行未报告 ASan 错误。

示例使用分别分配的对象与控制块，便于 ASan 检测对象内存释放后的访问。

本测试复现的是异步任务生命周期风险机制，
不是原服务器实际运行中的崩溃复现。

#
#include <functional>
#include <iostream>
#include <memory>
#include <string>

class ConnectionDemo {
private:
    int _value = 123;

public:
    ~ConnectionDemo() {
        std::cout << "对象析构" << std::endl;
    }

    void HandleTask() {
        // 必须实际访问对象成员，才能暴露释放后访问
        std::cout << "执行任务，value = "
                  << _value << std::endl;
    }
};

int main(int argc, char *argv[]) {
    if (argc != 2 ||
        (std::string(argv[1]) != "bad" &&
         std::string(argv[1]) != "good")) {
        std::cout << "用法：./lifetime_test bad 或 good\n";
        return 1;
    }

    bool use_strong_ref = std::string(argv[1]) == "good";

    // 模拟任务队列中暂未执行的任务
    std::function<void()> task;
    std::weak_ptr<ConnectionDemo> observer;

    {
        std::shared_ptr<ConnectionDemo> conn(new ConnectionDemo());
        observer = conn;

        if (use_strong_ref) {
            // 修复版本：任务保存一份强引用
            task = [conn]() {
                conn->HandleTask();
            };
        } else {
            // 问题版本：任务只保存裸指针
            ConnectionDemo *ptr = conn.get();
            task = [ptr]() {
                ptr->HandleTask();
            };
        }

        std::cout << "任务已排队，尚未执行" << std::endl;
    } // 模拟外部管理者释放连接引用

    std::cout << "外部引用已释放，对象是否销毁："
              << std::boolalpha << observer.expired()
              << std::endl;

    task();

    // 模拟任务执行完毕后，从任务队列中移除
    task = nullptr;

    std::cout << "任务已移除，对象是否销毁："
              << observer.expired() << std::endl;
}


g++ -std=c++11 -g -O1 -fsanitize=address \
  -fno-omit-frame-pointer lifetime_test.cc -o lifetime_test

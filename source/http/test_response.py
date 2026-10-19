import socket

HOST = "127.0.0.1"
PORT = 18085


def request(method, path, connection):
    return (
        f"{method} {path} HTTP/1.1\r\n"
        f"Host: localhost\r\n"
        f"Connection: {connection}\r\n"
        f"\r\n"
    ).encode("ascii")


def split_header(data):
    header, separator, remaining = data.partition(b"\r\n\r\n")
    assert separator, "没有完整响应头"

    lines = header.split(b"\r\n")
    parts = lines[0].split(b" ", 2)
    assert len(parts) == 3 and parts[0] == b"HTTP/1.1", (
        "响应边界错误：" + repr(lines[0])
    )
    status = int(parts[1])

    headers = {}
    for line in lines[1:]:
        key, value = line.split(b":", 1)
        key = key.strip().lower()
        headers.setdefault(key, []).append(value.strip())

    return status, headers, remaining


def check_case(method, path, expected_status,
               expected_length, expected_body):
    # 同一连接连续发送两个请求。
    # 第二个请求要求关闭，方便收集全部原始响应。
    outgoing = (
        request(method, path, "keep-alive")
        + request("GET", "/fixed", "close")
    )

    with socket.create_connection((HOST, PORT), timeout=5) as sock:
        sock.settimeout(5)
        sock.sendall(outgoing)

        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)

    data = b"".join(chunks)

    # 验证第一个响应
    status, headers, remaining = split_header(data)
    assert status == expected_status, (path, status)
    assert headers.get(b"connection") == [b"keep-alive"]
    assert b"transfer-encoding" not in headers

    if expected_length is None:
        assert b"content-length" not in headers, headers
    else:
        assert headers.get(b"content-length") == [
            str(expected_length).encode("ascii")
        ], headers

    assert remaining.startswith(expected_body), (
        "第一个响应正文不符合预期"
    )
    remaining = remaining[len(expected_body):]

    # 此处必须立即开始第二个响应。
    # HEAD 或 204 等如果偷偷多发了正文，这里就会失败。
    status, headers, remaining = split_header(remaining)

    assert status == 200
    assert headers.get(b"content-length") == [b"5"]
    assert headers.get(b"connection") == [b"close"]
    assert b"transfer-encoding" not in headers
    assert remaining == b"hello", (
        "第二个响应正文错误或有额外字节：" + repr(remaining)
    )

    print(f"PASS: {method} {path} -> 后续 GET 正常")


check_case("GET", "/fixed", 200, 5, b"hello")
check_case("GET", "/empty", 200, 0, b"")
check_case("HEAD", "/fixed", 200, None, b"")
check_case("GET", "/status/204", 204, None, b"")
check_case("GET", "/status/304", 304, None, b"")
check_case("GET", "/status/205", 205, 0, b"")

print("All response framing tests passed")
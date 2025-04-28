import socket  # noqa: F401
from socket import SHUT_RDWR
import selectors
import types
import argparse
from pathlib import Path
import gzip

def http_response(version,code,status,headers = None,body = None): # headers is a list of header / value tuples
    status_line = version + " " + str(code) + " " + status + "\r\n"
    header_line = ""
    if headers is not None:
        for header in headers:
            header_line = header_line + header[0] + ": " + str(header[1]) + "\r\n"
    if body is not None:
        if(isinstance(body,str)):
            response = (status_line + header_line + "\r\n" + body).encode("utf-8")
        else:
            response = (status_line + header_line + "\r\n").encode("utf-8") + body
    else:
        response = (status_line + header_line + "\r\n").encode("utf-8")
    return response

def process_request(socket,data,file_directory,selector):
    try:
        request_string = data.decode("utf-8")
    except:
        print("Data not decoded properly")
    try:
        request_line = request_string.split("\r\n")[0]
    except:
        print("Request not formatted correctly")
    try:
        method = request_line.split(" ")[0]
    except:
        print("Request Method not formatted correctly")
    try:
        target = request_line.split(" ")[1]
    except:
        print("Request Target not formatted correctly")
    try:
        version = request_line.split(" ")[2] 
    except:
        print("Request Version not formatted correctly")
    else:
        if(method == "GET"):
            http_get_response(socket,request_string,method,target,version,file_directory,selector)
        elif(method == "POST"):
            http_post_response(socket,request_string,method,target,version,file_directory,selector)

def http_post_response(socket,request_string,method,target,version,file_directory,selector):
    request_headers = (request_string.split("\r\n\r\n")[0]).split("\r\n")
    encoding_status = 0
    close_status = 0
    response_headers = []
    for header in request_headers:
        header_split = header.split(": ")
        if(len(header_split) > 1):
            header_key = header_split[0]
            header_value = header_split[1]
            if(str(header_key) == "Accept-Encoding"):
                encoding_schemes = header_value.split(",")
                for encoding in encoding_schemes:
                    encoding_wo_whitespace = ''.join(encoding.split())
                    if(str(encoding_wo_whitespace) == "gzip"):
                        encoding_status = 1
                        encoding_tuple = ["Content-Encoding","gzip"]
                        response_headers.append(encoding_tuple)
            if(str(header_key) == "Connection"):
                if(str(header_value) == "close"):
                    close_status = 1
                    connection_tuple = ["Connection","close"]
                    response_headers.append(connection_tuple)
    if(target[:7] == "/files/"):
        request_filename = target[7:len(target)]
        file_name = file_directory + request_filename
        file = open(file_name,"w")
        body = request_string.split("\r\n\r\n")[1]
        file.write(body)
        file.close()
        socket.sendall
        socket.sendall(http_response(version,201,"Created",response_headers))
        if(close_status):
            close_connection(socket,selector)
        return
    else:
        socket.sendall(http_response(version,404,"Not Found",response_headers))
        if(close_status):
            close_connection(socket,selector)
        return

def close_connection(socket,selector):
    try:
        socket.shutdown(SHUT_RDWR)
        selector.unregister(socket)
    except OSError:
        pass
    finally:
        socket.close()

def http_get_response(socket,request_string,method,target,version,file_directory,selector):
    request_headers = (request_string.split("\r\n\r\n")[0]).split("\r\n")
    encoding_status = 0
    close_status = 0
    response_headers = []
    for header in request_headers:
        header_split = header.split(": ")
        if(len(header_split) > 1):
            header_key = header_split[0]
            header_value = header_split[1]
            if(str(header_key) == "Accept-Encoding"):
                encoding_schemes = header_value.split(",")
                for encoding in encoding_schemes:
                    encoding_wo_whitespace = ''.join(encoding.split())
                    if(str(encoding_wo_whitespace) == "gzip"):
                        encoding_status = 1
                        encoding_tuple = ["Content-Encoding","gzip"]
                        response_headers.append(encoding_tuple)
            if(str(header_key) == "Connection"):
                if(str(header_value) == "close"):
                    close_status = 1
                    connection_tuple = ["Connection","close"]
                    response_headers.append(connection_tuple)
    if(target == "/"):
        socket.sendall(http_response(version,200,"OK",response_headers))
        if(close_status):
            close_connection(socket,selector)
        return
    if(target[:11] == "/user-agent"):
        for header in request_headers:
            header_split = header.split(": ")
            if(len(header_split) > 1):
                header_key = header_split[0]
                header_value = header_split[1]
                if(str(header_key) == "User-Agent"):
                    response_body = header_value
                    content_type_tuple = ["Content-Type","text/plain"]
                    response_headers.append(content_type_tuple) 
                    response_body_len = len(response_body)
                    content_length_tuple = ["Content-Length",response_body_len]
                    response_headers.append(content_length_tuple)
                    socket.sendall(http_response(version,200,"OK",response_headers,response_body))
                    if(close_status):
                        close_connection(socket,selector)
                    return
    elif(target[:6] == "/echo/"):
        content_type_tuple = ["Content-Type","text/plain"]
        response_headers.append(content_type_tuple)
        response_body = target[6:len(target)]
        if(encoding_status):
            response_body_encoded = response_body.encode('utf-8')
            compressed_body = gzip.compress(response_body_encoded)
            response_body_len = len(compressed_body)
            content_length_tuple = ["Content-Length",response_body_len]
            response_headers.append(content_length_tuple)
            socket.sendall(http_response(version,200,"OK",response_headers,compressed_body)) 
            if(close_status):
                close_connection(socket,selector)
            return
        else:
            response_body_len = len(response_body)
            content_length_tuple = ["Content-Length",response_body_len]
            response_headers.append(content_length_tuple)
            socket.sendall(http_response(version,200,"OK",response_headers,response_body)) 
            if(close_status):
                close_connection(socket,selector)
            return
    elif(target[:7] == "/files/"):
        request_filename = target[7:len(target)]
        directory = Path(file_directory)
        file_checker = 1
        for file in directory.iterdir():
            if file.is_file():
                content_type_tuple = ["Content-Type","application/octet-stream"]
                response_headers.append(content_type_tuple) 
                file_tokens = str(file).split('/')
                if str(file_tokens[len(file_tokens) - 1]) == request_filename:
                    file_checker = 0
                    file_size = file.stat().st_size
                    file_content = file.read_text(encoding="utf-8")
                    if(encoding_status):
                        response_body_encoded = file_content.encode('utf-8')
                        compressed_body = gzip.compress(response_body_encoded)
                        response_body_len = len(compressed_body)
                        content_length_tuple = ["Content-Length",response_body_len]
                        response_headers.append(content_length_tuple) 
                        socket.sendall(http_response(version,200,"OK",response_headers,compressed_body))
                        if(close_status):
                            close_connection(socket,selector)
                        return
                    else:
                        content_length_tuple = ["Content-Length",file_size]
                        response_headers.append(content_length_tuple)
                        socket.sendall(http_response(version,200,"OK",response_headers,file_content))
                        if(close_status):
                            close_connection(socket,selector)
                        return
        if(file_checker):
            socket.sendall(http_response(version,404,"Not Found",response_headers))
            if(close_status):
                close_connection(socket,selector)
            return
    else:
        socket.sendall(http_response(version,404,"Not Found",response_headers))
        if(close_status):
            close_connection(socket,selector)
        return

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', type=str)
    args = parser.parse_args()
    file_directory = args.directory
    sel = selectors.DefaultSelector()
    socket_server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socket_server.bind(("localhost",4221))
    socket_server.listen()
    socket_server.setblocking(False)
    sel.register(socket_server, selectors.EVENT_READ, data=None)
    try:
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    conn, addr = socket_server.accept()
                    print(f"Accepted connection from {addr}")
                    conn.setblocking(False)
                    conn_data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
                    event_types = selectors.EVENT_READ | selectors.EVENT_WRITE
                    sel.register(conn, event_types, data = conn_data)
                else:
                    conn = key.fileobj
                    conn_data = key.data
                    if mask & selectors.EVENT_READ:
                        data = conn.recv(1024)
                        if not data:
                            sel.unregister(conn)
                            conn.close()
                        else:
                            process_request(conn,data,file_directory,sel)
    except Exception as e:
        print(f"Some error occurred, not sure what. {e}")
    finally:
        sel.close()

if __name__ == "__main__":
    main()
#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# StreapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict

import asyncio
import inspect
import secrets
import time

# Import streaprous raw connection functions
from streaprous_socket.streaprous_raw_connection import (
    run_conn_recv,
    run_conn_send,
    close_connection
)
SESSIONS = {}
LOGIN_REQUIRED = {
    ("POST", "/submit-info/"),
    ("POST", "/add-list/"),
    ("GET", "/get-list/"),
}
class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
        conn_info (conn_struct): streaprous connection info for raw socket.
        raw_socket (socket): Raw socket for streaprous communication.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
        "conn_info",
        "raw_socket",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()
        #: streaprous connection info
        self.conn_info = None
        #: raw socket for streaprous communication
        self.raw_socket = None

    def read_request(self, read_more):
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = read_more()
            if not chunk:
                return data
            data += chunk

        head, _, body = data.partition(b"\r\n\r\n")

        #  Find content length in header
        length = 0
        for line in head.split(b"\r\n"):
            name, _, value = line.partition(b":")
            if name.strip().lower() == b"content-length":
                length = int(value.strip())

        while len(body) < length:
            chunk = read_more()
            if not chunk:
                break
            body += chunk

        return head + b"\r\n\r\n" + body

    def send_request(self, send, read_more, method, path, body="", host="", cookie=""):
        # Build the request with the Request helpers (RFC 9112 section 2.1)
        r = Request()
        r.method = method
        r.path = path
        r.headers = {
            "Host": host,
            "Content-Type": "application/json",
            "Connection": "close",
        }
        r.prepare_body(body)
        if cookie:
            r.prepare_cookies(cookie)
        send(r.to_bytes())

        # Read the response
        response = self.read_request(read_more)
        if not response:
            return 0, ""

        # Status line "HTTP/1.1 200 OK" -> 200 
        head, _, resp_body = response.partition(b"\r\n\r\n")
        status_line = head.split(b"\r\n")[0]
        status = int(status_line.split(b" ")[1])
        return status, resp_body.decode("utf-8")
    
    def call_hook(self, req, resp):
        user = SESSIONS.get(req.cookies.get("session"))
        # 401
        if (req.method, req.path) in LOGIN_REQUIRED and user is None:
            print("[HttpAdapter] Unauthorized {} {}".format(req.method, req.path))
            result = b'{"error": "Unauthorized"}'
            resp.status_code = 401
            resp.reason = "Unauthorized"
        else:
            try:
                # Tell handler who logged in 
                req.headers["username"] = user or ""
                result = req.hook(headers=req.headers, body=req.body)
                # async def handler: run the coroutine
                if inspect.iscoroutine(result):
                    result = asyncio.run(result)
                # Login handler return (body, username)
                if isinstance(result, tuple):
                    result, username = result
                    session_id = secrets.token_hex(16)
                    SESSIONS[session_id] = username
                    resp.cookies = {"session": session_id}
                resp.status_code = 200
                resp.reason = "OK"
            except Exception as e:
                print("[HttpAdapter] Route handler error: {}".format(e))
                result = b'{"error": "Internal Server Error"}'
                resp.status_code = 500
                resp.reason = "Internal Server Error"

        resp.headers["Content-Type"] = "application/json"
        resp._content = result
        return resp.build_response_header(req) + result

    def handle_client(self, conn, addr, routes):
        """
        Handle an incoming client connection.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """

        # Connection handler.
        self.conn = conn
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        # Handle the request
        msg = conn.recv(1024).decode()
        req.prepare(msg, routes)
        print("[HttpAdapter] Invoke handle_client connection {}".format(addr))

        # Handle request hook
        response = b""
        try:
            if req.hook:
                #
                # TODO: handle for App hook here
                #
                response = b""
            else:
                # Build response
                response = resp.build_response(req)
        except Exception as e:
            print("[HttpAdapter] Error building response: {}".format(e))
            response = b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\n\r\n"

        #print("[HttpAdapter] Response content {}".format(response))
        conn.sendall(response)
        conn.close()

    def handle_client_raw(self, raw_socket, conn_info, routes):
        """
        Handle an incoming client connection using streaprous raw connection.

        This method reads the request from the raw socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client using raw sockets.

        :param raw_socket (socket): The raw socket for communication.
        :param conn_info (conn_struct): The connection info for the client.
        :param routes (dict): The route mapping for dispatching requests.
        """
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        print("[HttpAdapter] Invoke handle_client_raw for {}:{}".format(conn_info.client_ip, conn_info.client_port))

        # Receive data using streaprous raw connection
        # data = run_conn_recv(raw_socket, conn_info)
        data = self.read_request(lambda: run_conn_recv(raw_socket, conn_info))

        if not data:
            print("[HttpAdapter] No data received or connection closed")
            return

        # Prepare request
        msg = data.decode("utf-8")
        req.prepare(msg, routes)

        # Handle request hook
        if req.hook:
            #
            # TODO: handle for App hook here
            #
            # response = ""
            response = self.call_hook(req, resp)
        else:
            # Build response - returns bytes
            response = resp.build_response(req)

        # Send response using streaprous raw connection
        response = response if isinstance(response, bytes) else response.encode("utf-8")
        print(f"[HttpAdapter] HTTP Response ({len(response)} bytes): {response[:200]}")
        #
        # TODO run_conn_send packet
        # run_conn_send(..)
        run_conn_send(raw_socket, conn_info, response)

        # Wait longer to ensure response is transmitted, client processes it, and sends ACK
        import time
        time.sleep(5.0)

        # Close connection with FIN packet
        #
        # TODO run_conn_send packet
        # close_connection(...)
        close_connection(raw_socket, conn_info)

    async def handle_client_coroutine(self, reader, writer):
        """
        Handle an incoming client connection using stream reader writer asynchronously.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        print("[HttpAdapter] Invoke handle_client_coroutine connection {})".format(addr))
        addr = writer.get_extra_info("peername")

        # TODO Handle the request asynchronously
        msg = await reader.read(1024)

        req.prepare(msg.decode("utf-8"), routes={})

        # Handle request hook
        if req.hook:
            #
            # TODO: handle for App hook here
            #
            response = ""

        # Build response
        # print("[HttpAdapter] Start **ASYNC** build_response with type {}".format(type(req)))
        response = resp.build_response(req)

        # Send all the response asynchronously
        writer.write(response)
        await writer.drain()

    @property
    def extract_cookies(self, req, resp):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        cookies = {}
        for header in headers:
            if header.startswith("Cookie:"):
                cookie_str = header.split(":", 1)[1].strip()
                for pair in cookie_str.split(";"):
                    key, value = pair.strip().split("=")
                    cookies[key] = value
        return cookies

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object 

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        response = Response()

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        response.cookies = extract_cookies(req)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    def build_json_response(self, req, resp):
        """Builds a :class:`Response <Response>` object from JSON data

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        response = Response(req)

        # Set encoding.
        response.raw = resp

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    # def get_connection(self, url, proxies=None):
    # """Returns a url connection for the given URL.

    # :param url: The URL to connect to.
    # :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
    # :rtype: int
    # """

    # proxy = select_proxy(url, proxies)

    # if proxy:
    # proxy = prepend_scheme_if_needed(proxy, "http")
    # proxy_url = parse_url(proxy)
    # if not proxy_url.host:
    # raise InvalidProxyURL(
    # "Please check proxy URL. It is malformed "
    # "and could be missing the host."
    # )
    # proxy_manager = self.proxy_manager_for(proxy)
    # conn = proxy_manager.connection_from_url(url)
    # else:
    # # Only scheme should be lower case
    # parsed = urlparse(url)
    # url = parsed.geturl()
    # conn = self.poolmanager.connection_from_url(url)

    # return conn

    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        
        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        username, password = ("user1", "password")

        if username:
            headers["Proxy-Authorization"] = (username, password)

        return headers

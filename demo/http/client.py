from demo.server import server

def main():
    # Send GET request to /hello
    response = server.send_request("/hello", method="GET")
    print("Response from /hello:", response)

    # Send POST request to /add with data
    response = server.send_request("/add", method="POST", data={"a": 7, "b": 5})
    print("Response from /add:", response)

if __name__ == "__main__":
    main()
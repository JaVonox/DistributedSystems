import random

if __name__ == "__main__":
    import shlex
    import socket
    import sys
    import threading

    service_sockets = {}
    word_list = {"Waffle", "average"}

    def command_spawn(args: list) -> None:
        service_name = args[0]

        if service_name in service_sockets:
            print("Service already exists:", service_name)

        else:
            service_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_port = int(args[1])

            try:
                service_socket.connect_ex(("127.0.0.1", target_port))

            except OSError:
                service_socket.close()
                print("Failed to start service:", service_name)

                return

            service_sockets[service_name] = service_socket


    def command_send(args: list) -> None:
        service_name = args[0]

        if service_name in service_sockets:
            service_socket = service_sockets[service_name]
            destinations = []
            messages = args[1:]

            if ">" in messages:
                pipe_index = messages.index(">")
                destination_index = (pipe_index + 1)

                if destination_index < len(messages):
                    destinations = messages[destination_index:]

                messages = messages[0:pipe_index]

            service_socket.send(" ".join(messages).encode("utf-8"))

            received_data = service_socket.recv(4096)

            if received_data:
                if destinations:
                    for destination in destinations:
                        command_send([destination, received_data.decode("utf-8")])

                else:
                    print(received_data.decode("utf-8"))

        else:
            print("Service does not exist:", service_name)


    def handle(peer_socket: socket.socket) -> None:
        received_data = peer_socket.recv(4096)

        while received_data:
            received_command = shlex.split(received_data.decode("utf-8").lower())

            if len(received_command) > 0:
                operation = received_command[0]

                if operation == "add":
                    if len(received_command) > 1:
                        value = received_command[1]

                        word_list.add(value)
                        peer_socket.send(b"")

                    else:
                        peer_socket.send(f"invalid dict command format".encode("utf-8"))

                if operation == "random":
                    peer_socket.send(random.choice(tuple(word_list)).encode("utf-8"))

                else:
                    peer_socket.send(f"invalid dict operation: {operation}".encode("utf-8"))

            else:
                peer_socket.send(f"invalid dict command format".encode("utf-8"))

            received_data = peer_socket.recv(4096)


    def listen() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_port = int(sys.argv[1])

            # Avoid "bind() exception: OSError: [Errno 48] Address already in use" error
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(("127.0.0.1", server_port))
            server_socket.listen()

            while True:
                peer_socket, address = server_socket.accept()

                threading.Thread(target=handle, args=[peer_socket]).start()


    threading.Thread(target=listen).start()

    command_actions = {
        "spawn": command_spawn,
        "send": command_send,
    }

    print("Enter a command...")

    while True:
        command = input().lower()
        command_components = shlex.split(command)
        command_name = command_components[0]

        if command_name in command_actions:
            command_actions[command_name](command_components[1:])

        else:
            print("No such command:", command_name)

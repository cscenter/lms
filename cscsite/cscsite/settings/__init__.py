import socket


# Note(lebedev): this is currently hardcoded for AWS server.
if socket.gethostname() == "ip-10-82-139-53":
    from . import production
else:
    from . import local

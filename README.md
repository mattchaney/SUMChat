Assignment 5 'SUMChat' by Matt Chaney - Thread Implementation

To run a server:
	./SUMChatServer <port>

To run a client:
	./SUMChatClient <host> <port> <s|u|m>

UMChatServer will accept UMChatClient connections from unicast, multicast or sctp clients, send address information upon receiving a connection request, and send the list password and exit password. 

The server will forward messages from all clients to each of the other clients. A client may sends the list password to the server by pressing Ctrl-C, and the server will send the list of all connected clients. If a client needs to exit it will send the exit password and be removed from the server's list of connected clients.

*** Note: I also made sure to send the exit pwd when the server exits as well, which will cause all clients to terminate.

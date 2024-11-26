import struct

def encode_message(header, port, payload):
    """
    Encode message with header and payload
    :param header: str, message header
    :param port: int, message port
    :param payload: str, message payload
    :return: bytes, encoded message
    """
    # Header is fixed-size string (5 bytes)
    header_bytes = header.encode()
    # Port is 2 bytes in network byte order
    port_bytes = struct.pack('>H', port)
    # Payload is the remaining part
    payload_bytes = payload.encode()
    # Concatenate all parts
    return header_bytes + port_bytes + payload_bytes


def decode_message(data):
    """
    Decode message with header, port, and payload
    :param data: bytes, encoded message
    :return: tuple(header, port, payload)
    """
    # Extract header (first 5 bytes)
    header = data[:5].decode()
    # Extract port (next 2 bytes)
    port = struct.unpack('>H', data[5:7])[0]
    # Extract payload (remaining bytes)
    payload = data[7:].decode()
    return header, port, payload


if __name__ == "__main__":
    # Test the encoding and decoding
    encoded = encode_message("TEXT ", 50051, "Hello World!")
    print(encoded)  # Output: b'TEXT \xc3\x13Hello World!'
    
    decoded = decode_message(encoded)
    print(decoded)  # Output: ('TEXT ', 50051, 'Hello World!')

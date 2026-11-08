import argparse
import socket
import sys
import struct

from utils import PacketHeader, compute_checksum

type_data = 2
type_ack = 3
type_end = 1
type_start = 0


def receiver(receiver_ip, receiver_port, window_size):
    """TODO: Listen on socket and print received message to sys.stdout."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    expected_seq_num = 0
    buffer = {}
    connected = False
    sender_address = None

    while True:
        # Receive packet; address includes both IP and port
        pkt, address = s.recvfrom(2048)

        # Extract header and payload
        pkt_header = PacketHeader(pkt[:16])
        msg = pkt[16 : 16 + pkt_header.length]

        packet_type = pkt_header.type
        seq_num = pkt_header.seq_num



        # Verity checksum
        pkt_checksum = pkt_header.checksum
        pkt_header.checksum = 0
        computed_checksum = compute_checksum(pkt_header / msg)
        if pkt_checksum != computed_checksum:
            continue

        if packet_type == type_start:
            if connected:
                continue

            connected = True
            sender_address = address

            ack_header = PacketHeader(type=type_ack, seq_num=seq_num, length=0, checksum=0)
            ack_header.checksum = compute_checksum(bytes(ack_header))
            s.sendto(bytes(ack_header), address)
            continue

        if not connected or address != sender_address:
            continue

        if packet_type == type_end:
            ack_header = PacketHeader(type=type_ack, seq_num=seq_num, length=0, checksum=0)
            ack_header.checksum = compute_checksum(bytes(ack_header))
            s.sendto(bytes(ack_header), address)
            
           
            if expected_seq_num == seq_num:
                break
            continue

        if packet_type == type_data:
            
            if seq_num >= expected_seq_num + window_size:
                continue

            
            if seq_num < expected_seq_num:
                ack_header = PacketHeader(type=type_ack, seq_num=seq_num, length=0, checksum=0)
                ack_header.checksum = compute_checksum(bytes(ack_header))
                s.sendto(bytes(ack_header), address)
                continue

            
            if seq_num >= expected_seq_num and seq_num not in buffer:
                buffer[seq_num] = msg

            
            while expected_seq_num in buffer:
                sys.stdout.buffer.write(buffer[expected_seq_num])
                sys.stdout.buffer.flush()
                del buffer[expected_seq_num]
                expected_seq_num += 1

            
            ack_seq = expected_seq_num - 1 
            ack_header = PacketHeader(type=type_ack, seq_num=ack_seq, length=0, checksum=0)
            
            
            ack_header.checksum = compute_checksum(bytes(ack_header))
            
            
            s.sendto(bytes(ack_header), address)
            
    s.close() 



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "receiver_ip", help="The IP address of the host that receiver is running on"
    )
    parser.add_argument(
        "receiver_port", type=int, help="The port number on which receiver is listening"
    )
    parser.add_argument(
        "window_size", type=int, help="Maximum number of outstanding packets"
    )
    args = parser.parse_args()

    receiver(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()

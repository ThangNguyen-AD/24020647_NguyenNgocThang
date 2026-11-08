import argparse
import socket
import sys
import time

from utils import PacketHeader, compute_checksum


type_data = 2
type_ack = 3
type_end = 1
type_start = 0

packet_size = 1024


def sender(receiver_ip, receiver_port, window_size):
    """TODO: Open socket and send message from sys.stdin."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    start_header = PacketHeader(type=type_start, seq_num=0, length=0)
    start_header.checksum = compute_checksum(bytes(start_header))
    start_pkt = bytes(start_header)

    start_connected = False
    while not start_connected:
        s.sendto(start_pkt, (receiver_ip, receiver_port))
        try:
            data, _ = s.recvfrom(2048)
            ack_pkt = PacketHeader(data)
            # Chỉ thoát lặp khi nhận đúng ACK
            if ack_pkt.type == type_ack:
                start_connected = True
        except socket.timeout:
            continue

    message = sys.stdin.buffer.read()

    chunks = []

    for i in range(0, len(message), packet_size):
        chunks.append(message[i:i+packet_size])

    num_packet = len(chunks)

    if num_packet == 0:
        chunks = [b'']
        num_packet = 1

    base = 0
    next_seq_num = 0

    packet = {}
    acked_packets = set()

    s.settimeout(0.5)

    while base < num_packet:
        while next_seq_num < base + window_size and next_seq_num < num_packet:
            load = chunks[next_seq_num]
            pkt_header = PacketHeader(type=type_data, seq_num=next_seq_num, length=len(load))

            pkt_header.checksum = compute_checksum(pkt_header/load)

            pkt_send = pkt_header/load

            s.sendto(bytes(pkt_send), (receiver_ip, receiver_port))
            packet[next_seq_num] = bytes(pkt_send)
            next_seq_num += 1

        try:
            data, _ = s.recvfrom(2048)
            ack_pkt = PacketHeader(data)

            if ack_pkt.type == type_ack:
                ack_num = ack_pkt.seq_num

                acked_packets.add(ack_num)

                while base in acked_packets:
                    if base in packet:
                        del packet[base] 
                    base += 1

                    for seq in list(packet.keys()):
                        if seq <= ack_num:
                            del packet[seq]

        except socket.timeout:
            for seq in range(base, next_seq_num):
                if seq not in acked_packets and seq in packet:
                    s.sendto(packet[seq], (receiver_ip, receiver_port))

            
    end_header = PacketHeader(type=type_end, seq_num=next_seq_num, length=0, checksum=0)
    end_header.checksum = compute_checksum(bytes(end_header))
    end_pkt = bytes(end_header)

    while True:
        s.sendto(end_pkt, (receiver_ip, receiver_port))
        try:
            data, _ = s.recvfrom(2048)
            ack_pkt = PacketHeader(data)
            if ack_pkt.type == type_ack and ack_pkt.seq_num == next_seq_num:
                break 
        except socket.timeout:
            continue 
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

    sender(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()

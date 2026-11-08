import argparse
import socket
import sys

from utils import PacketHeader, compute_checksum

type_data = 2
type_ack = 3
type_end = 1
type_start = 0

def receiver(receiver_ip, receiver_port, window_size):
    """TODO: Listen on socket and print received message to sys.stdout."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    expected_seq = 0
    pkt_buffer = {}

    while True:
        # Receive packet; address includes both IP and port
        pkt, address = s.recvfrom(2048)

        if len(pkt) < 16:
            continue

        
        pkt_header = PacketHeader(pkt[:16])
        msg = pkt[16 : 16 + pkt_header.length]

        
        pkt_checksum = pkt_header.checksum
        pkt_header.checksum = 0
        computed_checksum = compute_checksum(pkt_header / msg)
        if pkt_checksum != computed_checksum:
            continue

        if pkt_header.type == type_start:
            ack = PacketHeader(type=type_ack, seq_num=pkt_header.seq_num, length=0, checksum=0)
            ack.checksum = compute_checksum(ack / b"")
            s.sendto(bytes(ack / b""), address)
            continue

        if pkt_header.type == type_end:
            ack = PacketHeader(type=type_ack, seq_num=pkt_header.seq_num,
                               length=0, checksum=0)
            ack.checksum = compute_checksum(ack / b"")
            s.sendto(bytes(ack / b""), address)
            sys.stdout.buffer.flush()
            break

        if pkt_header.type != type_data:
            continue

        seq = pkt_header.seq_num

        if seq >= expected_seq + window_size:
            continue

        if seq < expected_seq:
            ack = PacketHeader(type=type_ack, seq_num=seq, length=0, checksum=0)
            ack.checksum = compute_checksum(ack / b"")
            s.sendto(bytes(ack / b""), address)
            continue

        if seq not in pkt_buffer:
            pkt_buffer[seq] = msg

        while expected_seq in pkt_buffer:
            sys.stdout.buffer.write(pkt_buffer[expected_seq])
            sys.stdout.buffer.flush()
            del pkt_buffer[expected_seq]
            expected_seq += 1
        
        ack = PacketHeader(type=type_ack, seq_num=seq, length=0, checksum=0)
        ack.checksum = compute_checksum(ack / b'')
        s.sendto(bytes(ack / b''), address)
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

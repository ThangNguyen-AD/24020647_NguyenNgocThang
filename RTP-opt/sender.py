import argparse
import socket
import sys
import time
import select

from utils import PacketHeader, compute_checksum

type_data = 0
type_ack = 1
type_end = 2
type_start = 3

time_out = 0.5
pay_load = 1024

def sender(receiver_ip, receiver_port, window_size):
    """TODO: Open socket and send message from sys.stdin."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setblocking(False)

    address = (receiver_ip, receiver_port)

    start_seq = 0

    while True:
        pkt_hdr = PacketHeader(type=type_start, seq_num=start_seq, length=0, checksum=0)
        pkt_hdr.checksum = compute_checksum(pkt_hdr/ b'')
        s.sendto(bytes(pkt_hdr/ b''), address)

        ready, _, _ = select.select([s], [], [], time_out)
        if not ready:
            continue
        try:
            pkt, _ = s.recvfrom(2048)
        except BlockingIOError:
            continue

        if len(pkt) < 16:
            continue

        header = PacketHeader(pkt[:16])
        load = pkt[16:16+header.length]
        check = header.checksum
        header.checksum = 0
        if check == compute_checksum(header/load) and header.type == type_ack and header.seq_num == start_seq:
            break

    data = sys.stdin.buffer.read()

    chunks = []

    for i in range(0, len(data), pay_load):
        chunks.append(data[i:i+pay_load])

    total = len(chunks)

    base = 0
    next_seq = 0
    acked = {}
    timers = {}

    while base < total:
        while next_seq < base + window_size and next_seq < total:
            pkt_hr = PacketHeader(type=type_data, seq_num=next_seq, length=len(chunks[next_seq]),checksum=0)
            pkt_hr.checksum = compute_checksum(pkt_hr/chunks[next_seq])
            s.sendto(bytes(pkt_hr/chunks[next_seq]), address)
            acked[next_seq] = False
            timers[next_seq] = time.time()
            next_seq += 1

        now = time.time()
        time_out_val  = time_out

        if timers:
            min_remaining = time_out
            for seq, t in list(timers.items()):
                elapsed = now - t
                if elapsed >= time_out:
                    
                    pkt_hr = PacketHeader(type=type_data, seq_num=seq, length=len(chunks[seq]), checksum=0)
                    pkt_hr.checksum = compute_checksum(pkt_hr/chunks[seq])
                    s.sendto(bytes(pkt_hr/chunks[seq]), address)
                    timers[seq] = time.time()
                    elapsed = 0
                
               
                remaining = time_out - elapsed
                if remaining < min_remaining:
                    min_remaining = remaining
            
            time_out_val = max(0.0, min_remaining)

        r, _, _ = select.select([s], [], [], time_out_val)
        if not r:
            continue

        while True:
            try:
                pkt, _ = s.recvfrom(2048)
            except BlockingIOError:
                break
            if len(pkt) < 16:
                continue

            h = PacketHeader(pkt[:16])
            load = pkt[16:16+h.length]
            chk = h.checksum
            h.checksum = 0
            if chk != compute_checksum(h/load) or h.type != type_ack:
                continue

            ack_seq = h.seq_num

            if base <= ack_seq < next_seq:
                acked[ack_seq] = True

                if ack_seq in timers:
                    del timers[ack_seq]

                advanced = False
                while acked.get(base, False):
                    del acked[base]
                    base += 1
                    advanced = True

                if base == next_seq:
                    timer_run = False
                elif advanced:
                    timer_start = time.time()

    end_seq = 0
        
    while not False:
        pkt_h = PacketHeader(type=type_end, seq_num=end_seq, length=3, checksum=0)
        pkt_h.checksum = compute_checksum(pkt_h/ b"END")
        s.sendto(bytes(pkt_h/ b"END"), address)

        ready, _, _ = select.select([s], [], [], time_out)
        if not ready:
            continue
        try:
                pkt, _ = s.recvfrom(2048)
        except BlockingIOError:
            continue
        if len(pkt) < 16:
            continue
        hh = PacketHeader(pkt[:16])
        load = pkt[16:16 + hh.length]
        chk = hh.checksum
        hh.checksum = 0
        if chk == compute_checksum(hh / load) and hh.type == type_ack and hh.seq_num == end_seq:
                break
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

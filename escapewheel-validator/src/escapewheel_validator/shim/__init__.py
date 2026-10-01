"""The checks of how a packet is stored, which a query over its tables cannot make (Part 05 §5.3).

time_origin
    A session's declared origin against its earliest mapped start.
floors
    A resource's encoding against the reader floor, and what was not assessed.
owned
    A packet-owned resource's payload names and recorded digest.
arrays
    A packet-owned array's metadata, and an array's shape against the tables describing it.
"""

__all__: list[str] = []

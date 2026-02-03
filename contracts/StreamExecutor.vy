# pragma version 0.4.3
"""
@title StreamExecutor
@author Curve.Fi
@license Copyright (c) Curve.Fi, 2025 - all rights reserved
@notice Execute due streams and forward rewards to the caller.
"""

N_MAX_EXECUTE: constant(uint256) = 32
N_MAX_VIEW: constant(uint256) = 1024
STREAMER: constant(address) = 0x2b786BB995978CC2242C567Ae62fd617b0eBC828


interface DonationStreamer:
    def streams_and_rewards_due(
    ) -> (DynArray[uint256, N_MAX_VIEW], DynArray[uint256, N_MAX_VIEW]): view
    def execute_many(
        stream_ids: DynArray[uint256, N_MAX_EXECUTE]
    ) -> DynArray[bool, N_MAX_EXECUTE]: nonpayable


@external
@payable
def __default__():
    pass


@internal
def _execute_due():
    due_ids: DynArray[uint256, N_MAX_VIEW] = empty(DynArray[uint256, N_MAX_VIEW])
    rewards: DynArray[uint256, N_MAX_VIEW] = empty(DynArray[uint256, N_MAX_VIEW])
    due_ids, rewards = staticcall DonationStreamer(STREAMER).streams_and_rewards_due()

    chunk: DynArray[uint256, N_MAX_EXECUTE] = empty(DynArray[uint256, N_MAX_EXECUTE])
    for i: uint256 in range(len(due_ids), bound=N_MAX_VIEW):
        chunk.append(due_ids[i])
        if len(chunk) == N_MAX_EXECUTE:
            extcall DonationStreamer(STREAMER).execute_many(chunk)
            chunk = empty(DynArray[uint256, N_MAX_EXECUTE])

    if len(chunk) > 0:
        extcall DonationStreamer(STREAMER).execute_many(chunk)

    if self.balance > 0:
        send(msg.sender, self.balance)


@external
def execute():
    self._execute_due()

# pragma version 0.4.3
"""
@title DonationPool
@author Curve.Fi
@license Copyright (c) Curve.Fi, 2025 - all rights reserved
@notice Per-pool donation streams that add liquidity on a schedule.
"""

from ethereum.ercs import IERC20


interface DonationPoolTarget:
    def add_liquidity(
        amounts: uint256[2],
        min_mint_amount: uint256,
        receiver: address,
        donation: bool,
    ) -> uint256: nonpayable


event StreamCreated:
    stream_id: uint256
    donor: indexed(address)
    amounts: uint256[N_COINS]
    period_length: uint256
    n_periods: uint256
    reward_per_period: uint256

event StreamExecuted:
    stream_id: uint256
    caller: indexed(address)
    periods: uint256
    amounts: uint256[N_COINS]
    reward_paid: uint256

event StreamCancelled:
    stream_id: uint256
    donor: indexed(address)
    amounts: uint256[N_COINS]
    reward_refund: uint256


struct DonationStream:
    donor: address
    amounts_remaining: uint256[N_COINS]
    amounts_per_period: uint256[N_COINS]
    period_length: uint256
    periods_remaining: uint256
    next_ts: uint256
    reward_per_period: uint256


N_COINS: constant(uint256) = 2
MAX_BATCH: constant(uint256) = 32
N_MAX_VIEW: constant(uint256) = 1024

pool: public(immutable(address))
coins: public(immutable(address[N_COINS]))

stream_count: public(uint256)
streams: public(HashMap[uint256, DonationStream])


@deploy
def __init__(
    _pool: address,
    _coins: address[N_COINS],
):
    assert _pool != empty(address), "pool required"
    assert _coins[0] != empty(address) and _coins[1] != empty(address), "coin required"
    assert _coins[0] != _coins[1], "same coin"

    pool = _pool
    coins = _coins


@external
@payable
@nonreentrant
def create_stream(
    amounts: uint256[N_COINS],
    period_length: uint256,
    n_periods: uint256,
    reward_per_period: uint256,
) -> uint256:
    assert n_periods > 0, "bad n_periods"
    assert period_length > 0, "bad period_length"
    assert amounts[0] > 0 or amounts[1] > 0, "zero amounts"
    reward_total: uint256 = reward_per_period * n_periods
    assert msg.value == reward_total, "reward mismatch"

    amounts_per_period: uint256[N_COINS] = empty(uint256[N_COINS])
    for i: uint256 in range(N_COINS):
        amount: uint256 = amounts[i]
        if amount > 0:
            assert extcall IERC20(coins[i]).transferFrom(msg.sender, self, amount), "transfer failed"
        amounts_per_period[i] = amount // n_periods

    stream_id: uint256 = self.stream_count
    self.stream_count = stream_id + 1

    stream: DonationStream = DonationStream(
        donor=msg.sender,
        amounts_remaining=amounts,
        amounts_per_period=amounts_per_period,
        period_length=period_length,
        periods_remaining=n_periods,
        next_ts=block.timestamp + period_length,
        reward_per_period=reward_per_period,
    )

    self.streams[stream_id] = stream
    log StreamCreated(
        stream_id=stream_id,
        donor=msg.sender,
        amounts=amounts,
        period_length=period_length,
        n_periods=n_periods,
        reward_per_period=reward_per_period,
    )

    return stream_id


@internal
def _approve_if_needed(token: address, amount: uint256):
    if amount == 0:
        return

    allowance: uint256 = staticcall IERC20(token).allowance(self, pool)
    if allowance < amount:
        assert extcall IERC20(token).approve(pool, max_value(uint256)), "approve failed"


@internal
@view
def _due_periods(stream: DonationStream) -> uint256:
    if stream.donor == empty(address):
        return 0
    if stream.periods_remaining == 0 or stream.period_length == 0:
        return 0
    if block.timestamp < stream.next_ts:
        return 0

    periods_due: uint256 = (block.timestamp - stream.next_ts) // stream.period_length + 1
    if periods_due > stream.periods_remaining:
        periods_due = stream.periods_remaining
    return periods_due


@view
@external
def is_due(stream_id: uint256) -> bool:
    stream: DonationStream = self.streams[stream_id]
    return self._due_periods(stream) > 0


@view
@external
def streams_due(n_max: uint256 = N_MAX_VIEW) -> DynArray[uint256, N_MAX_VIEW]:
    due_ids: DynArray[uint256, N_MAX_VIEW] = empty(DynArray[uint256, N_MAX_VIEW])
    count: uint256 = self.stream_count
    if count == 0:
        return due_ids

    limit: uint256 = count
    if limit > N_MAX_VIEW:
        limit = N_MAX_VIEW
    if n_max != 0 and n_max < limit:
        limit = n_max

    for i: uint256 in range(limit, bound=N_MAX_VIEW):
        stream_id: uint256 = count - 1 - i
        stream: DonationStream = self.streams[stream_id]
        if self._due_periods(stream) > 0:
            due_ids.append(stream_id)

    return due_ids


@view
@external
def rewards_due(
    stream_ids: DynArray[uint256, N_MAX_VIEW],
    n_max: uint256 = N_MAX_VIEW,
) -> DynArray[uint256, N_MAX_VIEW]:
    rewards: DynArray[uint256, N_MAX_VIEW] = empty(DynArray[uint256, N_MAX_VIEW])
    count: uint256 = len(stream_ids)

    limit: uint256 = count
    if limit > N_MAX_VIEW:
        limit = N_MAX_VIEW
    if n_max != 0 and n_max < limit:
        limit = n_max

    for i: uint256 in range(limit, bound=N_MAX_VIEW):
        stream_id: uint256 = stream_ids[count - 1 - i]
        stream: DonationStream = self.streams[stream_id]
        rewards.append(stream.reward_per_period * self._due_periods(stream))

    return rewards


@internal
def _execute_streams(stream_ids: DynArray[uint256, MAX_BATCH]) -> (uint256, uint256):
    executed: uint256 = 0
    reward_total: uint256 = 0
    count: uint256 = len(stream_ids)

    for i: uint256 in range(count, bound=MAX_BATCH):
        stream_id: uint256 = stream_ids[i]
        stream: DonationStream = self.streams[stream_id]

        periods_due: uint256 = self._due_periods(stream)
        if periods_due == 0:
            continue

        amounts_to_send: uint256[N_COINS] = empty(uint256[N_COINS])
        for j: uint256 in range(N_COINS):
            remaining: uint256 = stream.amounts_remaining[j]
            if remaining == 0:
                continue
            per_period: uint256 = stream.amounts_per_period[j]
            amount: uint256 = per_period * periods_due
            if periods_due == stream.periods_remaining:
                amount = remaining
            amounts_to_send[j] = amount
            stream.amounts_remaining[j] = remaining - amount

        stream.periods_remaining -= periods_due
        stream.next_ts += stream.period_length * periods_due
        if stream.periods_remaining == 0:
            stream.donor = empty(address)

        self.streams[stream_id] = stream

        for j: uint256 in range(N_COINS):
            self._approve_if_needed(coins[j], amounts_to_send[j])

        if amounts_to_send[0] > 0 or amounts_to_send[1] > 0:
            extcall DonationPoolTarget(pool).add_liquidity(
                amounts_to_send,
                0,
                empty(address),
                True,
            )

        reward_paid: uint256 = stream.reward_per_period * periods_due
        reward_total += reward_paid
        executed += 1

        log StreamExecuted(
            stream_id=stream_id,
            caller=msg.sender,
            periods=periods_due,
            amounts=amounts_to_send,
            reward_paid=reward_paid,
        )

    return executed, reward_total


@internal
def _execute_and_pay(stream_ids: DynArray[uint256, MAX_BATCH]) -> uint256:
    executed: uint256 = 0
    reward_total: uint256 = 0
    executed, reward_total = self._execute_streams(stream_ids)

    if reward_total > 0:
        send(msg.sender, reward_total)

    return executed


@external
@nonreentrant
def execute_many(stream_ids: DynArray[uint256, MAX_BATCH]) -> uint256:
    return self._execute_and_pay(stream_ids)


@external
@nonreentrant
def execute_one(stream_id: uint256) -> uint256:
    stream_ids: DynArray[uint256, MAX_BATCH] = empty(DynArray[uint256, MAX_BATCH])
    stream_ids.append(stream_id)

    return self._execute_and_pay(stream_ids)


@external
@nonreentrant
def cancel_stream(stream_id: uint256):
    stream: DonationStream = self.streams[stream_id]
    assert stream.donor != empty(address), "inactive"
    assert stream.donor == msg.sender, "donor only"

    amounts_refund: uint256[N_COINS] = stream.amounts_remaining
    reward_refund: uint256 = stream.reward_per_period * stream.periods_remaining
    self.streams[stream_id] = DonationStream(
        donor=empty(address),
        amounts_remaining=empty(uint256[N_COINS]),
        amounts_per_period=empty(uint256[N_COINS]),
        period_length=0,
        periods_remaining=0,
        next_ts=0,
        reward_per_period=0,
    )

    for i: uint256 in range(N_COINS):
        if amounts_refund[i] > 0:
            assert extcall IERC20(coins[i]).transfer(msg.sender, amounts_refund[i]), "refund failed"

    if reward_refund > 0:
        send(msg.sender, reward_refund)

    log StreamCancelled(
        stream_id=stream_id,
        donor=msg.sender,
        amounts=amounts_refund,
        reward_refund=reward_refund,
    )

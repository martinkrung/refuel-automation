# pragma version 0.4.3
"""
@title DonationStreamer
@author Curve.Fi
@license Copyright (c) Curve.Fi, 2025 - all rights reserved
@notice Permissionless donation streams that add liquidity on a schedule.
"""

from ethereum.ercs import IERC20


############### INTERFACES #################
interface DonationPoolTarget:
    def add_liquidity(
        amounts: uint256[2],
        min_mint_amount: uint256,
        receiver: address,
        donation: bool,
    ) -> uint256: nonpayable
    def coins(i: uint256) -> address: view


################ EVENTS ###################
event StreamCreated:
    stream_id: uint256
    donor: indexed(address)
    pool: indexed(address)
    amounts: uint256[N_COINS]
    period_length: uint256
    n_periods: uint256
    reward_per_period: uint256


event StreamExecuted:
    stream_id: uint256
    caller: indexed(address)
    pool: indexed(address)
    periods: uint256
    amounts: uint256[N_COINS]
    reward_paid: uint256


event StreamCancelled:
    stream_id: uint256
    donor: indexed(address)
    pool: indexed(address)
    amounts: uint256[N_COINS]
    reward_refund: uint256


################ DATA ####################
struct DonationStream:
    # Static
    donor: address
    pool: address
    coins: address[N_COINS]
    amounts_per_period: uint256[N_COINS]
    period_length: uint256
    reward_per_period: uint256
    # Dynamic
    next_ts: uint256
    reward_remaining: uint256
    amounts_remaining: uint256[N_COINS]
    periods_remaining: uint256


N_COINS: constant(uint256) = 2
N_MAX_EXECUTE: constant(uint256) = 32
N_MAX_VIEW: constant(uint256) = 1024

stream_count: public(uint256)
streams: public(HashMap[uint256, DonationStream])


################ INIT ####################
@deploy
def __init__():
    """
    @notice Initialize the donation streamer.
    """
    pass


############ INTERNAL HELPERS ############
@internal
def _increase_allowance(token: address, spender: address, amount: uint256):
    """
    @dev Increase allowance for a pool by amount.
    """
    assert extcall IERC20(token).approve(
        spender,
        staticcall IERC20(token).allowance(self, spender) + amount,
    ), "approve failed"


@internal
def _decrease_allowance(token: address, spender: address, amount: uint256):
    """
    @dev Decrease allowance for a pool by amount, floored at zero.
    """
    allowance: uint256 = staticcall IERC20(token).allowance(self, spender)
    if amount > allowance:
        assert extcall IERC20(token).approve(spender, 0), "approve failed"
    else:
        assert extcall IERC20(token).approve(spender, allowance - amount), "approve failed"




@internal
@view
def _due_periods(stream: DonationStream) -> uint256:
    """
    @dev Return the number of due periods for a stream.
    """
    if (
        stream.donor == empty(address)
        or stream.periods_remaining == 0
        or stream.period_length == 0
        or block.timestamp < stream.next_ts
    ):
        return 0

    return min(
        (block.timestamp - stream.next_ts) // stream.period_length + 1,
        stream.periods_remaining,
    )


@internal
@view
def _streams_due(n_max: uint256) -> DynArray[uint256, N_MAX_VIEW]:
    """
    @dev Collect due stream ids from newest to oldest.
    """
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
        if self._due_periods(self.streams[stream_id]) > 0:
            due_ids.append(stream_id)
    return due_ids


@internal
def _execute_stream(stream_id: uint256) -> bool:
    """
    @dev Execute a single stream if due and pay its reward.
    """
    stream: DonationStream = self.streams[stream_id]
    periods_due: uint256 = self._due_periods(stream)
    if periods_due == 0:
        return False

    is_final: bool = periods_due == stream.periods_remaining
    pool: address = stream.pool

    amounts_to_send: uint256[N_COINS] = empty(uint256[N_COINS])
    for j: uint256 in range(N_COINS):
        remaining: uint256 = stream.amounts_remaining[j]
        if remaining == 0:
            continue
        amount: uint256 = stream.amounts_per_period[j] * periods_due
        if is_final:
            amount = remaining
        amounts_to_send[j] = amount
        stream.amounts_remaining[j] = remaining - amount

    stream.periods_remaining -= periods_due
    stream.next_ts += stream.period_length * periods_due

    reward_paid: uint256 = stream.reward_per_period * periods_due
    if is_final:
        reward_paid = stream.reward_remaining
    stream.reward_remaining -= reward_paid

    if is_final:
        self.streams[stream_id] = empty(DonationStream)
    else:
        self.streams[stream_id] = stream

    if amounts_to_send[0] > 0 or amounts_to_send[1] > 0:
        extcall DonationPoolTarget(pool).add_liquidity(
            amounts_to_send,
            0,
            empty(address),
            True,
        )

    if reward_paid > 0:
        send(msg.sender, reward_paid)
    log StreamExecuted(
        stream_id=stream_id,
        caller=msg.sender,
        pool=pool,
        periods=periods_due,
        amounts=amounts_to_send,
        reward_paid=reward_paid,
    )

    return True


############### EXTERNAL VIEW ############
@view
@external
def is_due(stream_id: uint256) -> bool:
    """
    @notice Return true if the stream can be executed now.
    """
    return self._due_periods(self.streams[stream_id]) > 0


@view
@external
def streams_due(n_max: uint256 = N_MAX_VIEW) -> DynArray[uint256, N_MAX_VIEW]:
    """
    @notice Return up to n_max due stream ids, newest first.
    @dev Not meant to be called onchain; iterates over up to N_MAX_VIEW streams.
    """
    return self._streams_due(n_max)


@view
@external
def view_executable(n_max: uint256 = N_MAX_VIEW) -> DynArray[uint256, N_MAX_VIEW]:
    """
    @notice Alias for streams_due.
    @dev Not meant to be called onchain; iterates over up to N_MAX_VIEW streams.
    """
    return self._streams_due(n_max)


@view
@external
def rewards_due(
    stream_ids: DynArray[uint256, N_MAX_VIEW],
    n_max: uint256 = N_MAX_VIEW,
) -> DynArray[uint256, N_MAX_VIEW]:
    """
    @notice Return due rewards for the latest stream ids.
    @dev Not meant to be called onchain; iterates over up to N_MAX_VIEW ids.
    """
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
        periods_due: uint256 = self._due_periods(stream)
        if periods_due == 0:
            rewards.append(0)
        elif periods_due == stream.periods_remaining:
            rewards.append(stream.reward_remaining)
        else:
            rewards.append(stream.reward_per_period * periods_due)
    return rewards


############### EXTERNAL ACTIONS #########
@external
@payable
@nonreentrant
def create_stream(
    pool: address,
    coins: address[N_COINS],
    amounts: uint256[N_COINS],
    period_length: uint256,
    n_periods: uint256,
    reward_per_period: uint256,
) -> uint256:
    """
    @notice Create a donation stream for a pool.
    """
    assert pool != empty(address), "pool required"
    assert coins[0] != empty(address) and coins[1] != empty(address), "coin required"
    assert coins[0] != coins[1], "same coin"
    assert n_periods > 0, "bad n_periods"
    assert period_length > 0, "bad period_length"
    assert amounts[0] > 0 or amounts[1] > 0, "zero amounts"

    assert (
        coins[0] == staticcall DonationPoolTarget(pool).coins(0)
        and coins[1] == staticcall DonationPoolTarget(pool).coins(1)
    ), "coin mismatch"

    assert msg.value >= reward_per_period * n_periods, "reward mismatch"

    amounts_per_period: uint256[N_COINS] = empty(uint256[N_COINS])
    for i: uint256 in range(N_COINS):
        amount: uint256 = amounts[i]
        if amount > 0:
            assert extcall IERC20(coins[i]).transferFrom(
                msg.sender, self, amount, default_return_value=True
            ), "transfer failed"
            self._increase_allowance(coins[i], pool, amount)
        amounts_per_period[i] = amount // n_periods

    stream_id: uint256 = self.stream_count
    self.stream_count = stream_id + 1

    self.streams[stream_id] = DonationStream(
        donor=msg.sender,
        pool=pool,
        coins=coins,
        amounts_per_period=amounts_per_period,
        period_length=period_length,
        reward_per_period=reward_per_period,
        next_ts=block.timestamp,
        reward_remaining=msg.value,
        amounts_remaining=amounts,
        periods_remaining=n_periods,
    )

    log StreamCreated(
        stream_id=stream_id,
        donor=msg.sender,
        pool=pool,
        amounts=amounts,
        period_length=period_length,
        n_periods=n_periods,
        reward_per_period=reward_per_period,
    )

    return stream_id


@external
@nonreentrant
def execute_many(stream_ids: DynArray[uint256, N_MAX_EXECUTE]) -> DynArray[bool, N_MAX_EXECUTE]:
    """
    @notice Execute a batch of stream ids.
    @return Per-stream execution results in input order.
    """
    results: DynArray[bool, N_MAX_EXECUTE] = empty(DynArray[bool, N_MAX_EXECUTE])
    for i: uint256 in range(len(stream_ids), bound=N_MAX_EXECUTE):
        results.append(self._execute_stream(stream_ids[i]))
    return results


@external
@nonreentrant
def execute(stream_id: uint256) -> bool:
    """
    @notice Execute a single stream id.
    """
    return self._execute_stream(stream_id)


@external
@nonreentrant
def cancel_stream(stream_id: uint256):
    """
    @notice Cancel a stream and refund remaining balances.
    """
    stream: DonationStream = self.streams[stream_id]
    assert stream.donor != empty(address), "inactive"
    assert stream.donor == msg.sender, "donor only"

    pool: address = stream.pool
    coins: address[N_COINS] = stream.coins
    amounts_refund: uint256[N_COINS] = stream.amounts_remaining
    reward_refund: uint256 = stream.reward_remaining
    self.streams[stream_id] = empty(DonationStream)

    for i: uint256 in range(N_COINS):
        if amounts_refund[i] > 0:
            self._decrease_allowance(coins[i], pool, amounts_refund[i])
            assert extcall IERC20(coins[i]).transfer(
                msg.sender, amounts_refund[i], default_return_value=True
            ), "refund failed"
    if reward_refund > 0:
        send(msg.sender, reward_refund)

    log StreamCancelled(
        stream_id=stream_id,
        donor=msg.sender,
        pool=pool,
        amounts=amounts_refund,
        reward_refund=reward_refund,
    )

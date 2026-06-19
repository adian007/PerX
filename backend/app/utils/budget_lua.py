"""Atomic budget decrement — check-and-DECRBY in one Redis operation."""

BUDGET_DECR_LUA = """
local key = KEYS[1]
local amount = tonumber(ARGV[1])
local current = tonumber(redis.call('GET', key) or '0')
if current < amount then
    return -1
end
return redis.call('DECRBY', key, amount)
"""

import pytest
from brownie import Wei


def test_increasing_debt_limit(gov, hegic, hegicStaking, vault, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})

    # Start with a 888k debt limit
    vault.addStrategy(strategy, Wei("888000 ether"), 2 ** 256 - 1, 0, {"from": gov})

    # deposit 888001 in total to test
    vault.deposit(Wei("888000 ether"), {"from": gov})
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1

    # Deposit 888k more
    vault.deposit(Wei("888000 ether"), {"from": gov})
    # harvest() shouldn't do anything since debtLimit is still 888k
    strategy.harvest()
    assert hegic.balanceOf(strategy) == 0

    # Once debt limit moves to 888k * 2, strategy should buy the second lot
    vault.updateStrategyDebtLimit(strategy, Wei("1776000 ether"))
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 2


def test_decrease_debt_limit(gov, hegic, hegicStaking, vault, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})

    # Start with a 888k * 2 debt limit
    vault.addStrategy(strategy, Wei("1776000 ether"), 2 ** 256 - 1, 0, {"from": gov})

    # Depositing 888k * 2 should buy two lots
    vault.deposit(Wei("1776000 ether"), {"from": gov})
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 2

    # let's lower the debtLimit so the strategy adjust it's position
    vault.updateStrategyDebtLimit(strategy, Wei("888000 ether"))
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1
    assert vault.debtOutstanding(strategy) == 0

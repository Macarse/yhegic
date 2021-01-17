import pytest
import brownie
from brownie import Wei


def test_increasing_debt_limit(gov, hegic, hegicStaking, vault, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})

    # Start with a 888k deposit limit
    vault.setDepositLimit(Wei("888000 ether"), {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 0, {"from": gov})

    # deposit 888k in total to test
    vault.deposit(Wei("888000 ether"), {"from": gov})
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1

    # User shouldn't be able to deposit 888k more
    with brownie.reverts():
        vault.deposit(Wei("888000 ether"), {"from": gov})

    # Once deposit limit moves to 888k * 2, strategy should buy the second lot
    vault.setDepositLimit(Wei("1776000 ether"), {"from": gov})
    vault.deposit(Wei("888000 ether"), {"from": gov})
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 2


def test_decrease_debt_limit(gov, hegic, hegicStaking, vault, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})

    vault.setDepositLimit(Wei("1776000 ether"), {"from": gov})
    # Start with 100% of the debt
    vault.addStrategy(strategy, 10_000, 0, 0, {"from": gov})

    # Depositing 888k * 2 should buy two lots
    vault.deposit(Wei("1776000 ether"), {"from": gov})
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 2

    # let's lower the debtLimit so the strategy adjust it's position
    vault.updateStrategyDebtRatio(strategy, 5_000)
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1
    assert vault.debtOutstanding(strategy) == 0

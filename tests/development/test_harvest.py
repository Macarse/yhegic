import pytest
from brownie import Wei


def test_buy_stake(gov, vault, hegic, hegicStaking, strategy):

    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.addStrategy(strategy, hegic.balanceOf(gov), 2 ** 256 - 1, 0, {"from": gov})
    # deposit 1MM in total to test
    vault.deposit(Wei("1000000 ether"), {"from": gov})
    strategy.harvest()

    assert hegicStaking.balanceOf(strategy) == 1
    assert hegic.balanceOf(strategy) == Wei("112000 ether")


def test_harvest(gov, vault, hegic, hegicStaking, strategy, rewards, strategist):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.addStrategy(
        strategy,
        hegic.balanceOf(gov),
        2 ** 256 - 1,
        50,  # 50 bps fee for strategist
        {"from": gov},
    )
    # deposit 888k in total to test
    vault.deposit(Wei("888000 ether"), {"from": gov})
    strategy.harvest()

    # Hegic should be all invested
    assert hegic.balanceOf(strategy) == 0

    # Both should have 0 eth
    assert hegicStaking.balance() == 0
    assert strategy.balance() == 0

    hegicStaking.sendProfit({"value": Wei("1 ether")})
    assert hegicStaking.balance() == Wei("1 ether")
    strategy.harvest()

    # hegicStaking should have distributed earned eth
    assert hegicStaking.balance() == 0

    # Strategy should have converted those eth into hegic
    assert strategy.balance() == 0
    assert hegic.balanceOf(strategy) == 0

    # Rewards is getting management fees + performance fees
    # 1 hegic is 0.00032502 through the mockUni, so total profit is 3070
    # 3070 * 0.045 = 138.15
    assert vault.balanceOf(rewards) > Wei("138 ether")
    assert vault.balanceOf(rewards) < Wei("138.5 ether")

    # 3070 * 0.005 is 15.35
    assert vault.balanceOf(strategist) > Wei("15.35 ether")
    assert vault.balanceOf(strategist) < Wei("16 ether")

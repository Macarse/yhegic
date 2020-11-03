import pytest
from brownie import Wei


def test_hegic_donations(gov, vault, hegic, hegicStaking, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})
    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})

    vault.addStrategy(
        strategy, Wei("888000 ether"), 2 ** 256 - 1, 0, {"from": gov},
    )

    vault.deposit(Wei("888000 ether"), {"from": gov})

    # Send want directly to the strategy (DONT DO THIS)
    hegic.transferFrom(gov, strategy, Wei("100 ether"), {"from": gov})
    strategy.harvest({"from": gov})
    assert hegicStaking.balanceOf(strategy) == 1

    strategyParams = vault.strategies(strategy).dict()
    assert strategyParams["totalReturns"] == 0

    hegicStaking.sendProfit({"value": Wei("1 ether")})
    assert hegicStaking.balanceOf(strategy) == 1
    strategy.harvest({"from": gov})

    # Need to call again to update params values
    strategyParams = vault.strategies(strategy).dict()

    # Donation will not be marked as profit, it will stay in strategy
    # reserves until the next adjustPosition has enough to buy a lot
    assert strategyParams["totalReturns"] == Wei("3076 ether")
    assert strategyParams["totalDebt"] == Wei("888000 ether")
    assert hegic.balanceOf(strategy) == Wei("100 ether")


def test_ether_donations(gov, vault, hegic, hegicStaking, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})
    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})

    vault.addStrategy(
        strategy, Wei("888000 ether"), 2 ** 256 - 1, 0, {"from": gov},
    )

    vault.deposit(Wei("888000 ether"), {"from": gov})
    strategy.harvest({"from": gov})
    assert hegicStaking.balanceOf(strategy) == 1
    strategyParams = vault.strategies(strategy).dict()
    assert strategyParams["totalReturns"] == 0

    # Send eth directly to the strategy (DONT DO THIS)
    gov.transfer(strategy, Wei("1 ether"))
    hegicStaking.sendProfit({"value": Wei("1 ether")})
    assert hegicStaking.balanceOf(strategy) == 1
    strategy.harvest({"from": gov})

    # Need to call again to update params values
    strategyParams = vault.strategies(strategy).dict()

    # Donation will be marked as profit, since there will be more
    # eth converted to hegic
    assert strategyParams["totalReturns"] == Wei("6153 ether")
    assert strategyParams["totalDebt"] == Wei("888000 ether")
    assert hegic.balanceOf(strategy) == 0

import pytest
import brownie
from brownie import Wei


def test_min_deposit(vault, gov, hegic, hegicStaking, strategy):
    # Minimal constructor test
    assert strategy.name() == "StrategyHegic"

    # Send 1 hegic which shouldn't be enough to buy a lot
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.addStrategy(strategy, hegic.balanceOf(gov), 2 ** 256 - 1, 0, {"from": gov})
    vault.deposit(Wei("1 ether"), {"from": gov})

    strategy.harvest()
    assert hegic.balanceOf(strategy) == Wei("1 ether")
    assert hegicStaking.balanceOf(strategy) == 0


def test_initial_balances(gov, hegic, hegicStaking, vault, strategy):
    vault.addStrategy(strategy, hegic.balanceOf(gov), 2 ** 256 - 1, 0, {"from": gov})

    assert strategy.balanceOfWant() == 0
    assert strategy.balanceOfStake() == 0
    assert strategy.ethFutureProfit() == 0
    assert strategy.hegicFutureProfit() == 0


def test_balances(gov, hegic, hegicStaking, vault, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.addStrategy(strategy, hegic.balanceOf(gov), 2 ** 256 - 1, 0, {"from": gov})

    # deposit 888001 in total to test
    vault.deposit(Wei("888001 ether"), {"from": gov})
    strategy.harvest()
    hegicStaking.sendProfit({"value": Wei("1 ether")})

    assert strategy.balanceOfWant() == Wei("1 ether")
    assert strategy.balanceOfStake() == Wei("888000 ether")
    assert strategy.ethFutureProfit() == Wei("1 ether")
    assert strategy.hegicFutureProfit() == Wei("3076 ether")


def test_protected_tokens(strategy, hegic, hegicStaking):
    with brownie.reverts():
        tokens = strategy.sweep(hegic)

    with brownie.reverts():
        tokens = strategy.sweep(hegicStaking)


def test_estimated_total_assets(strategy, gov, hegic, hegicStaking):
    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})
    hegicStaking.approve(gov, 2 ** 256 - 1, {"from": gov})

    # For test simplicity, transfer to the strategy without going through the vault
    hegic.transferFrom(gov, strategy, Wei("100 ether"), {"from": gov})
    hegicStaking.transferFrom(gov, strategy, 1, {"from": gov})

    assert strategy.estimatedTotalAssets() == Wei("888100 ether")

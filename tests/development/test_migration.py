import pytest
import brownie
from brownie import Wei


def test_migration(
    gov, hegic, hegicStaking, vault, strategy, strategist, bob, alice, strategy2
):
    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})
    hegic.transferFrom(gov, bob, Wei("800000 ether"))
    hegic.transferFrom(gov, alice, Wei("100000 ether"))

    vault.setManagementFee(0)
    hegic.approve(vault, 2 ** 256 - 1, {"from": bob})
    hegic.approve(vault, 2 ** 256 - 1, {"from": alice})
    vault.deposit(hegic.balanceOf(bob), {"from": bob})
    vault.deposit(hegic.balanceOf(alice), {"from": alice})
    vault.addStrategy(strategy, 10_000, 0, 0, {"from": gov})

    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1
    assert hegic.balanceOf(strategy) == Wei("12000 ether")
    assert hegic.balanceOf(vault) == 0

    # Only Governance can migrate
    with brownie.reverts():
        vault.migrateStrategy(strategy, strategy2, {"from": bob})
    with brownie.reverts():
        vault.migrateStrategy(strategy, strategy2, {"from": alice})
    with brownie.reverts():
        vault.migrateStrategy(strategy, strategy2, {"from": strategist})

    strategy.migrate(strategy2, {"from": gov})
    assert hegicStaking.balanceOf(strategy) == 0
    assert hegic.balanceOf(strategy) == 0

    assert hegicStaking.balanceOf(strategy2) == 1
    assert hegic.balanceOf(strategy2) == Wei("12000 ether")

    assert hegic.balanceOf(vault) == 0


def test_migration_missing_profit(
    gov, hegic, hegicStaking, vault, strategy, strategist, bob, alice, strategy2
):

    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})
    hegic.transferFrom(gov, bob, Wei("800000 ether"))
    hegic.transferFrom(gov, alice, Wei("100000 ether"))

    vault.setManagementFee(0)
    hegic.approve(vault, 2 ** 256 - 1, {"from": bob})
    hegic.approve(vault, 2 ** 256 - 1, {"from": alice})
    vault.deposit(hegic.balanceOf(bob), {"from": bob})
    vault.deposit(hegic.balanceOf(alice), {"from": alice})
    vault.addStrategy(strategy, 10_000, 0, 0, {"from": gov})

    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1
    assert hegic.balanceOf(strategy) == Wei("12000 ether")
    assert hegic.balanceOf(vault) == 0

    # Send profit
    hegicStaking.sendProfit({"value": Wei("1 ether")})
    assert hegicStaking.balance() == Wei("1 ether")
    assert strategy.hegicFutureProfit() > 0

    vault.migrateStrategy(strategy, strategy2, {"from": gov})

    assert hegicStaking.balanceOf(strategy) == 0
    assert hegic.balanceOf(strategy) == 0
    assert hegicStaking.balanceOf(strategy2) == 1
    assert hegic.balanceOf(strategy2) == Wei("12000 ether")

    # Can't re-add a strategy
    with brownie.reverts():
        vault.addStrategy(strategy, 0, 0, 0, {"from": gov})

    # But it can harvest
    strategy.harvest()
    assert strategy.hegicFutureProfit() == 0

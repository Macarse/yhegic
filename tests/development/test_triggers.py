import pytest
import brownie
from brownie import Wei, chain


def xtest_tend_trigger(strategy):
    assert strategy.tendTrigger(100) == False
    assert strategy.tendTrigger(0) == False


def test_harvest_trigger_when_profit(gov, vault, hegic, hegicStaking, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.addStrategy(strategy, Wei("888000 ether"), 2 ** 256 - 1, 0, {"from": gov})
    vault.deposit(Wei("888000 ether"), {"from": gov})
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1

    hegicStaking.sendProfit({"value": Wei("1 ether")})
    assert strategy.harvestTrigger(100) == True


def test_harvest_trigger_without_profit(gov, vault, hegic, hegicStaking, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.addStrategy(strategy, Wei("888000 ether"), 2 ** 256 - 1, 0, {"from": gov})
    vault.deposit(Wei("888000 ether"), {"from": gov})
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1
    assert strategy.harvestTrigger(1) == False


def test_harvest_trigger_with_profit(gov, vault, hegic, hegicStaking, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.addStrategy(strategy, Wei("888000 ether"), 2 ** 256 - 1, 0, {"from": gov})
    vault.deposit(Wei("888000 ether"), {"from": gov})
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1

    hegicStaking.sendProfit({"value": Wei("1 ether")})
    assert strategy.harvestTrigger(1) == True

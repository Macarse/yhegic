import pytest
import brownie

from brownie import Wei


def test_simple_withdrawal_888k(gov, hegic, hegicStaking, vault, strategy, bob, alice):
    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})
    hegic.transferFrom(gov, bob, Wei("888000 ether"))

    vault.setManagementFee(0)
    hegic.approve(vault, 2 ** 256 - 1, {"from": bob})
    vault.deposit(hegic.balanceOf(bob), {"from": bob})

    vault.addStrategy(strategy, 10_000, 0, 0, {"from": gov})

    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1
    assert hegic.balanceOf(strategy) == 0

    vault.withdraw(Wei("100 ether"), {"from": bob})
    assert hegic.balanceOf(bob) == Wei("100 ether")
    assert hegic.balanceOf(strategy) == Wei("887900 ether")
    assert hegic.balanceOf(vault) == 0


def test_simple_withdrawal_888001(
    gov, hegic, hegicStaking, vault, strategy, bob, alice
):
    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})
    hegic.transferFrom(gov, bob, Wei("888001 ether"))

    vault.setManagementFee(0)
    hegic.approve(vault, 2 ** 256 - 1, {"from": bob})
    vault.deposit(hegic.balanceOf(bob), {"from": bob})

    vault.addStrategy(strategy, 10_000, 0, 0, {"from": gov})

    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1
    assert hegic.balanceOf(strategy) == Wei("1 ether")

    vault.withdraw(Wei("100 ether"), {"from": bob})
    assert hegic.balanceOf(bob) == Wei("100 ether")
    assert hegic.balanceOf(strategy) == Wei("887901 ether")
    assert hegic.balanceOf(vault) == 0


def test_simple_withdrawal_1000(gov, hegic, hegicStaking, vault, strategy, bob, alice):
    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})
    hegic.transferFrom(gov, bob, Wei("1000 ether"))

    vault.setManagementFee(0)
    hegic.approve(vault, 2 ** 256 - 1, {"from": bob})
    vault.deposit(hegic.balanceOf(bob), {"from": bob})

    vault.addStrategy(strategy, 10_000, 0, 0, {"from": gov})

    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 0
    assert hegic.balanceOf(strategy) == Wei("1000 ether")

    vault.withdraw(Wei("100 ether"), {"from": bob})
    assert hegic.balanceOf(bob) == Wei("100 ether")
    assert hegic.balanceOf(strategy) == Wei("900 ether")
    assert hegic.balanceOf(vault) == 0


def test_simple_withdrawal_1776001(
    gov, hegic, hegicStaking, vault, strategy, bob, alice
):
    vault.setDepositLimit(Wei("1776002 ether"), {"from": gov})

    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})
    hegic.transferFrom(gov, bob, Wei("1776001 ether"))

    vault.setManagementFee(0)
    hegic.approve(vault, 2 ** 256 - 1, {"from": bob})
    vault.deposit(hegic.balanceOf(bob), {"from": bob})

    vault.addStrategy(strategy, 10_000, 0, 0, {"from": gov})

    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 2
    assert hegic.balanceOf(strategy) == Wei("1 ether")

    vault.withdraw(Wei("888001 ether"), {"from": bob})
    assert hegic.balanceOf(bob) == Wei("888001 ether")
    assert hegicStaking.balanceOf(strategy) == 1
    assert hegic.balanceOf(strategy) == 0

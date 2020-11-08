import pytest

from brownie import Wei


def test_exit_with_single_deposit(gov, hegic, hegicStaking, vault, strategy, bob):
    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})
    hegic.transferFrom(gov, bob, Wei("1000 ether"))

    vault.setManagementFee(0)
    hegic.approve(vault, 2 ** 256 - 1, {"from": bob})
    vault.deposit(hegic.balanceOf(bob), {"from": bob})
    vault.addStrategy(strategy, Wei("888000 ether"), 2 ** 256 - 1, 0, {"from": gov})

    assert vault.emergencyShutdown() == False
    vault.setEmergencyShutdown(True)
    assert vault.emergencyShutdown() == True

    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 0
    assert hegic.balanceOf(strategy) == 0

    vault.withdraw(Wei("100 ether"), {"from": bob})
    assert hegic.balanceOf(bob) == Wei("100 ether")
    assert hegic.balanceOf(vault) == Wei("900 ether")
    assert hegic.balanceOf(strategy) == 0


def test_exit_after_investment(gov, hegic, hegicStaking, vault, strategy, bob):
    hegic.approve(gov, 2 ** 256 - 1, {"from": gov})
    hegic.transferFrom(gov, bob, Wei("888000 ether"))

    vault.setManagementFee(0)
    hegic.approve(vault, 2 ** 256 - 1, {"from": bob})
    vault.deposit(hegic.balanceOf(bob), {"from": bob})
    vault.addStrategy(strategy, Wei("888000 ether"), 2 ** 256 - 1, 0, {"from": gov})

    assert vault.emergencyShutdown() == False
    strategy.harvest()
    assert hegicStaking.balanceOf(strategy) == 1
    assert hegic.balanceOf(strategy) == 0

    vault.setEmergencyShutdown(True)
    assert vault.emergencyShutdown() == True

    # Try getting some money out before full shutdown from vault
    vault.withdraw(Wei("100 ether"), {"from": bob})
    assert hegic.balanceOf(bob) == Wei("100 ether")
    assert hegic.balanceOf(vault) == 0
    assert hegic.balanceOf(strategy) == Wei("887900 ether")
    assert vault.debtOutstanding(strategy) == Wei("887900 ether")

    # Full shutdown
    vault.revokeStrategy(strategy)

    strategy.harvest()
    assert vault.debtOutstanding(strategy) == 0
    assert hegic.balanceOf(vault) == Wei("887900 ether")
    assert hegic.balanceOf(strategy) == 0

import pytest

from brownie import Wei, accounts, Contract, config
from brownie import StrategyHegicETH


@pytest.mark.require_network("mainnet-fork")
def test_hegic_strategy_infura(pm):
    hegic_liquidity = accounts.at(
        "0x736f85bf359e3e2db736d395ed8a4277123eeee1", force=True
    )  # Hegic: Liquidity M&U (lot's of hegic)

    rewards = accounts[2]
    gov = accounts[3]
    guardian = accounts[4]
    bob = accounts[5]
    alice = accounts[6]
    strategist = accounts[7]

    hegic = Contract("0x584bC13c7D411c00c01A62e8019472dE68768430", owner=gov)
    hegic.approve(hegic_liquidity, Wei("1000000 ether"), {"from": hegic_liquidity})
    hegic.transferFrom(
        hegic_liquidity, gov, Wei("888000 ether"), {"from": hegic_liquidity}
    )

    Vault = pm(config["dependencies"][0]).Vault
    yHegic = Vault.deploy({"from": gov})
    yHegic.initialize(hegic, gov, rewards, "", "")
    yHegic.setDepositLimit(Wei("889000 ether"))

    # HEGIC ETH Staking lot (hlETH)
    hegicStaking = Contract("0x1Ef61E3E5676eC182EED6F052F8920fD49C7f69a", owner=gov)

    # Sushiswap router v2
    uni = Contract("0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f", owner=gov)

    strategy = guardian.deploy(StrategyHegicETH, yHegic, hegic, hegicStaking, uni)
    strategy.setStrategist(strategist)

    # 100% of the vault's depositLimit
    yHegic.addStrategy(strategy, 10_000, 0, 0, {"from": gov})

    hegic.approve(gov, Wei("1000000 ether"), {"from": gov})
    hegic.transferFrom(gov, bob, Wei("100000 ether"), {"from": gov})
    hegic.transferFrom(gov, alice, Wei("788000 ether"), {"from": gov})
    hegic.approve(yHegic, Wei("1000000 ether"), {"from": bob})
    hegic.approve(yHegic, Wei("1000000 ether"), {"from": alice})

    yHegic.deposit(Wei("100000 ether"), {"from": bob})
    yHegic.deposit(Wei("788000 ether"), {"from": alice})

    strategy.harvest()

    assert hegic.balanceOf(strategy) == 0
    assert hegicStaking.balanceOf(strategy) == 1

    hegicStaking.sendProfit({"value": Wei("1 ether"), "from": gov})
    strategy.harvest({"from": gov})

    # We should have made profit
    assert yHegic.pricePerShare() / 1e18 > 1

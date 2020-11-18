import pytest

from brownie import Wei, accounts, Contract, config
from brownie import StrategyEthHegicLP


def test_rhegic_strategy_infura(pm):
    #probably not needed
    rhegic_liquidity = accounts.at(
        "0x8ac7de95ff8d0ee72e0b54f781ab2e18f27108fb", force=True
    )  # rHegic: deployer account with tons of rHegic (~3bil)

    # weth needed to test strategy
    weth_liquidity = accounts.at(
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", force=True
    )  # Maker vault (~2.6mil)

    rewards = accounts[2]
    gov = accounts[3]
    guardian = accounts[4]
    bob = accounts[5]
    alice = accounts[6]
    strategist = accounts[7]

    #original hegic changed to rHegic
    rHegic = Contract.from_explorer(
        "0x47C0aD2aE6c0Ed4bcf7bc5b380D7205E89436e84", owner=gov
    )  # rHegic token
    rHegic.approve(rhegic_liquidity, Wei("1000000 ether"), {"from": rhegic_liquidity})
    rHegic.transferFrom(
        rhegic_liquidity, gov, Wei("888000 ether"), {"from": rhegic_liquidity}
    )

    # vault deals with weth, so addresses need it.
    weth = Contract.from_explorer(
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", owner=gov
    )  # weth token
    weth.approve(weth_liquidity, Wei("1000000 ether"), {"from": weth_liquidity})
    weth.transferFrom(
        weth_liquidity, gov, Wei("888000 ether"), {"from": weth_liquidity}
    )

    # declaring yEthLP as the vault
    Vault = pm(config["dependencies"][-1]).Vault
    yEthLP = gov.deploy(Vault, weth, gov, rewards, "", "")

    ethPool = Contract.from_explorer(
        "0x878F15ffC8b894A1BA7647c7176E4C01f74e140b", owner=gov
    )  # ETH LP pool (writeETH)
    ethPoolStaking = Contract.from_explorer(
        "0x9b18975e64763bDA591618cdF02D2f14a9875981", owner=gov
    ) #ETH LP pool staking for rHegic
    uni = Contract.from_explorer(
        "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", owner=gov
    )  # UNI router v2

    strategy = guardian.deploy(StrategyEthHegicLP, yEthLP, rHegic, ethPool, ethPoolStaking, uni)
    strategy.setStrategist(strategist)

    #adding strategy to the vault
    yEthLP.addStrategy(strategy, Wei("888000 ether"), 2 ** 256 - 1, 50, {"from": gov})

    # original hegic changed to rHegic. Vault doesn't use rHegic so this is irrelevant
    #rHegic.approve(gov, Wei("1000000 ether"), {"from": gov})
   # rHegic.transferFrom(gov, bob, Wei("100000 ether"), {"from": gov})
    #rHegic.transferFrom(gov, alice, Wei("788000 ether"), {"from": gov})
    #rHegic.approve(yHegic, Wei("1000000 ether"), {"from": bob})
   # rHegic.approve(yHegic, Wei("1000000 ether"), {"from": alice})

    # folks need weth for the contract
    weth.approve(gov, Wei("10000 ether"), {"from": gov})
    weth.transferFrom(gov, bob, Wei("1000 ether"), {"from": gov})
    weth.transferFrom(gov, alice, Wei("7880 ether"), {"from": gov})
    weth.approve(yEthLP, Wei("10000 ether"), {"from": bob})
    weth.approve(yEthLP, Wei("10000 ether"), {"from": alice})

    yEthLP.deposit(Wei("1000 ether"), {"from": bob})
    #deposit lock. 70k blocks is just over 16 days. Maximum timelock is 15 days.
    chain.mine(Wei("70000 ether"))
    yEthLP.deposit(Wei("7880 ether"), {"from": alice})
    chain.mine(Wei("70000 ether"))

    strategy.harvest()
    chain.mine(Wei("70000 ether"))

    assert rHegic.balanceOf(strategy) == 0
    assert ethPool.balanceOf(strategy) == 0
    assert ethPoolStaking.balanceOf(strategy) == 1

    ethPoolStaking.sendProfit({"value": Wei("1 ether"), "from": gov})
    strategy.harvest({"from": gov})

    # We should have made profit
    assert yEthLP.pricePerShare() > 1

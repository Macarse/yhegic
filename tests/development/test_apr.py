import pytest
from brownie import Wei

ONE_DAY = 86_400
DAYS_PER_YEAR = ONE_DAY * 365


def stateOfVault(vault, strategy):
    print("\n----state of vault----")
    strState = vault.strategies(strategy)
    totalDebt = strState[5].to("ether")
    totalReturns = strState[6].to("ether")
    print(f"Total Strategy Debt: {totalDebt:.5f}")
    print(f"Total Strategy Returns: {totalReturns:.5f}")
    balance = vault.totalAssets().to("ether")
    print(f"Total Assets: {balance:.5f}")


def stateOfStrat(strategy, hegic, hegicStaking):
    print("\n----state of strat----")

    print("Hegic:", hegic.balanceOf(strategy).to("ether"))
    print("HegicStaking:", hegicStaking.balanceOf(strategy))
    print("total assets estimate:", strategy.estimatedTotalAssets().to("ether"))


def test_apr(gov, vault, hegic, hegicStaking, strategy):
    hegic.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.addStrategy(
        strategy,
        2 ** 256 - 1,
        2 ** 256 - 1,
        500,  # 500 bps fee for strategist
        {"from": gov},
    )

    vault.deposit(Wei("888000 ether"), {"from": gov})
    strategy.harvest()
    assert hegic.balanceOf(strategy) == 0
    startingBalance = vault.totalAssets()
    assert startingBalance == Wei("888000 ether")

    stateOfStrat(strategy, hegic, hegicStaking)
    stateOfVault(vault, strategy)

    for i in range(10):
        day = (1 + i) * ONE_DAY
        print(f"\n----Day {day/ONE_DAY}----")

        assert vault.creditAvailable(strategy) == 0
        hegicStaking.sendProfit({"value": Wei("0.1 ether")})
        strategy.harvest()
        stateOfStrat(strategy, hegic, hegicStaking)
        stateOfVault(vault, strategy)

        profit = (vault.totalAssets() - startingBalance).to("ether")
        strState = vault.strategies(strategy)
        totalReturns = strState[6]
        totaleth = totalReturns.to("ether")
        print(f"Real Profit: {profit:.5f}")

        day = (1 + i) * ONE_DAY
        apr = (totalReturns / startingBalance) * (DAYS_PER_YEAR / day)
        print(f"implied apr: {apr:.8%}")

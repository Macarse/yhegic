import pytest
from brownie import config
from brownie import FakeHegic, StrategyHegicETH, MockHegicStakingEth, MockUni


@pytest.fixture
def rewards(a):
    yield a[2]


@pytest.fixture
def gov(a):
    yield a[3]


@pytest.fixture
def guardian(a):
    yield a[4]


@pytest.fixture
def bob(a):
    yield a[5]


@pytest.fixture
def alice(a):
    yield a[6]


@pytest.fixture
def strategist(a):
    yield a[7]


@pytest.fixture
def hegic(gov):
    yield gov.deploy(FakeHegic)


@pytest.fixture
def vault(pm, gov, hegic, rewards):
    Vault = pm(config["dependencies"][0]).Vault
    yield gov.deploy(Vault, hegic, gov, rewards, "", "")


@pytest.fixture
def hegicStaking(gov, hegic):
    yield gov.deploy(MockHegicStakingEth, hegic)


@pytest.fixture
def uni(gov, hegic):
    yield gov.deploy(MockUni, hegic)


@pytest.fixture
def strategy(guardian, vault, hegic, hegicStaking, uni, strategist):
    strategy = guardian.deploy(StrategyHegicETH, vault, hegic, hegicStaking, uni)
    strategy.setStrategist(strategist)

    yield strategy


@pytest.fixture
def strategy2(guardian, vault, hegic, hegicStaking, uni, strategist):
    strategy = strategist.deploy(StrategyHegicETH, vault, hegic, hegicStaking, uni)
    strategy.setStrategist(strategist)

    yield strategy

// SPDX-License-Identifier: MIT

pragma experimental ABIEncoderV2;
pragma solidity 0.6.12;

import "@openzeppelinV3/contracts/token/ERC20/IERC20.sol";
import "@openzeppelinV3/contracts/math/SafeMath.sol";
import "@openzeppelinV3/contracts/math/Math.sol";
import "@openzeppelinV3/contracts/utils/Address.sol";
import "@openzeppelinV3/contracts/token/ERC20/SafeERC20.sol";
import {BaseStrategy, StrategyParams} from "@yearnvaults/contracts/BaseStrategy.sol";

import "../../interfaces/hegic/IHegicEthPoolStaking.sol";
import "../../interfaces/hegic/IHegicEthPool.sol";
import "../../interfaces/uniswap/Uni.sol";
import "../../interfaces/uniswap/IWeth.sol";

contract StrategyEthHegicLP is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    address public weth;
    address public hegic;
    address public rHegic;
    address public EthPoolStaking;
    address public EthPool;
    address public unirouter;
    string public constant override name = "StrategyEthHegicLP";

    constructor(
        address _weth,
        address _vault,
        address _hegic,
        address _rHegic,
        address _EthPoolStaking,
        address _EthPool,
        address _unirouter
    ) public BaseStrategy(_vault) {
        want = _weth;
        hegic = _hegic;
        rHegic = _rHegic;
        EthPoolStaking = _EthPoolStaking;
        EthPool = _EthPool;
        unirouter = _unirouter;

        // just in case there's some magic switch from rHegic -> HEGIC at some point in the future
        IERC20(hegic).safeApprove(EthPoolStaking, uint256(-1));
        IERC20(rHegic).safeApprove(EthPoolStaking, uint256(-1));
        IERC20(EthPool).safeApprove(EthPoolStaking, uint256(-1));
    }

    // for the weth->eth swap
    receive() external payable {}

    function protectedTokens() internal override view returns (address[] memory) {
        address[] memory protected = new address[](5);
        // same as above re: magic switch.
        protected[0] = hegic;
        protected[1] = rHegic;
        protected[2] = EthPool;
        protected[3] = EthPoolStaking;
        protected[4] = weth;
        return protected;
    }

    function depositLockRemaining() internal view returns (uint256) {
        uint256 timeDeposited = IHegicEthPool(EthPool).lastProvideTimestamp(address(this));
        uint256 timeLock = IHegicEthPool(EthPool).lockupPeriod().add(1 days);
        uint256 timeUnlocked = block.timestamp;

        return (timeUnlocked).sub((timeLock).add(timeDeposited));
    }

    function withdrawLockRemaining() internal view returns (uint256) {
        uint256 timeDeposited = IHegicEthPool(EthPool).lastProvideTimestamp(address(this));
        uint256 timeLock = IHegicEthPool(EthPool).lockupPeriod();
        uint256 timeUnlocked = block.timestamp;

        return (timeUnlocked).sub((timeLock).add(timeDeposited));
    }

    // just for the strategist to see whether this is allowed or not
    function depositLocked() public view returns (string) {
        uint256 locked = depositLockRemaining();
            if (locked <= 0) {
                return name = "Deposit available";
            }
            else {
                return name = "Deposit locked";
            }
    }

    // just for the strategist to see whether this is allowed or not
     function withdrawLocked() public view returns (string) {
        uint256 locked = withdrawLockRemaining();
            if (locked <= 0) {
                return name = "Withdraw available";
            }
            else {
                return name = "Withdraw locked";
            }
    }

    // returns sum of all assets, realized and unrealized
    function estimatedTotalAssets() public override view returns (uint256) {
        return balanceOfWant(address(this)).add(balanceOfStake()).add(balanceOfPool()).add(ethFutureProfit());
    }

    function prepareReturn(uint256 _debtOutstanding) internal override returns (uint256 _profit) {
       // We might need to return want to the vault
        if (_debtOutstanding > 0) {
           liquidatePosition(_debtOutstanding);
        }

        // Update reserve with the available want so it's not considered profit
        setReserve(balanceOfWant().sub(_debtOutstanding));

        // Claim profit only when available
        uint256 hegicProfit = hegicFutureProfit();
        if (hegicProfit > 0) {
            IHegicEthPoolStaking(ethPoolStaking).getReward();

            // swap rhegic available in the contract for weth
            uint256 _hegicBalance = IERC20(rhegic).balanceOf(address(this));
            _swap(_hegicBalance);
        }

        // Final profit is want generated in the swap if ethProfit > 0
        _profit = balanceOfWant().sub(getReserve());
    }


    // adjusts position. Will not deposit if timelock check fails.
    function adjustPosition(uint256 _debtOutstanding) internal override {
       //emergency exit is dealt with in prepareReturn
        if (emergencyExit) {
          return;
       }

        // Reset the reserve value before
        setReserve(0);

        // turn eth to weth - just so that funds are held in weth instead of eth.
        uint256 _ethBalance = address(this).balance;
        if (_ethBalance > 0) {
            swapEthtoWeth(_ethBalance);
        }

       // Invest the rest of the want
       uint256 _wantAvailable = balanceOfWant().sub(_debtOutstanding);
       uint256 depositLock = depositLockRemaining();
        if (depositLock <= 0 ) {
            if (_wantAvailable > 0) {
                // turn weth to Eth
                uint256 availableFunds = swapWethtoEth(_wantAvailable);
                // make sure approvals are properly set up in the constructor
                IHegicEthPool(ethPool).provide(availableFunds);
                uint256 writeEth = IERC20(ethPool).balanceOf(address(this));
                IHegicEthPoolStaking(ethPoolStaking).stake(writeEth);
            }
        }
    }

    // N.B. this will only work so long as the various contracts are not timelocked
    // each deposit into the ETH pool restarts the 14 day counter on the entire value.
        // we will have to include a deposit lockout for lockupPeriod()+1 days to allow exiting position
    function exitPosition() internal override {
        uint256 stakes = IERC20(EthPoolStaking).balanceOf(address(this));
        uint256 writeEth = IERC20(EthPool).balanceOf(address(this));
        uint256 _timeLock = withdrawLockRemaining();
        if (_timeLock <= 0) {
            IHegicEthPoolStaking(EthPoolStaking).exit();
            IHegicEthPool(EthPool).withdraw(writeEth);
            uint256 _ethBalance = address(this).balance();
            swapEthtoWeth(_ethBalance);
        }
        else return name = "withdrawal timelocked";
    }

    //this math only deals with want, which is weth.
    function liquidatePosition(uint256 _amountNeeded) internal override returns (uint256 _amountFreed) {
        if (balanceOfWant() < _amountNeeded) {
            // We need to sell stakes to get back more want
            _withdrawSome(_amountNeeded.sub(balanceOfWant()));
        }

        // Since we might free more than needed, let's send back the min
        _amountFreed = Math.min(balanceOfWant(), _amountNeeded);
    }


    // withdraw a fraction, if not timelocked
    function _withdrawSome(uint256 _amount) internal returns (uint256) {
        uint256 _amountWriteEth = (_amount).mul(writeEthRatio());
        // this should mean that we always withdraw the amount of writeEth we take from staking
        uint256 _amountBurn = (_amountWriteEth).add(1);
        if (withdrawLockRemaining() <= 0) {
            IHegicEthPoolStaking(EthPoolStaking).withdraw(_amountWriteEth);
            IHegicEthPool(ethPool).withdraw(_amountWriteEth, _amountBurn);
            // convert eth to want
            uint256 _ethBalance = address(this).balance();
            swapEthtoWeth(_ethBalance);
        }
        else return name = "withdrawal timelocked";
    }


    // it looks like this function transfers not just "want" tokens, but all tokens - including (un)staked writeEth.
    // I suppose this is only if the _newStrategy is based on the current strat, and isn't a full exit.
    function prepareMigration(address _newStrategy) internal override {
        want.transfer(_newStrategy, balanceOfWant());
        IERC20(ethPool).transfer(_newStrategy, IERC20(ethPool).balanceOf(address(this)));
        IERC20(ethPoolStaking).transfer(_newStrategy, IERC20(ethPoolStaking).balanceOf(address(this)));
    }

    // swaps rHegic for weth
    function _swap(uint256 _amountIn) internal returns (uint256[] memory amounts) {
        address[] memory path = new address[](2);
        path[0] = address(0x47c0ad2ae6c0ed4bcf7bc5b380d7205e89436e84); // rHegic
        //path[0] = address(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2); // weth
        path[1] = address(want);

        Uni(unirouter).swapExactTokensForTokens(_amountIn, uint256(0), path, address(this), now.add(1 days));
    }

    // calculates the eth that earned rHegic is worth
    function ethFutureProfit() public view returns (uint256) {
        uint256 hegicProfit = hegicFutureProfit();
        if (hegicProfit == 0) {
            return 0;
        }

        address[] memory path = new address[](2);
        path[0] = address(0x47c0ad2ae6c0ed4bcf7bc5b380d7205e89436e84); // rHegic
        path[1] = address(want);
        uint256[] memory amounts = Uni(unirouter).getAmountsOut(hegicProfit, path);

        return amounts[amounts.length - 1];
    }

    // returns (r)Hegic earned by the LP
    function hegicFutureProfit() public view returns (uint256) {
        return IHegicEthPoolStaking(EthPoolStaking).earned(address(this));
    }

    // returns ETH in the pool
    function balanceOfPool() public view returns (uint256) {
        uint256 writeEth = IERC20(EthPool).balanceOf(address(this));
        return (writeEth).div(writeEthRatio());
    }

    // returns pooled ETH that is staked
    function balanceOfStake() public view returns (uint256) {
        uint256 writeEth = IERC20(EthPoolStaking).balanceOf(address(this));
        return (writeEth).div(writeEthRatio());
    }

    // returns balance of wETH
    function balanceOfWant() public view returns (uint256) {
        return IERC20(want).balanceOf(address(this));
    }

    // calculates the current ETH:writeETH ratio. Should return approx ~1000
    function writeEthRatio() internal returns (uint256) {
        uint256 supply = IHegicEthPool(EthPool).totalSupply();
        uint256 balance = IHegicEthPool(EthPool).totalBalance();
        uint256 rate = 0;
        if (supply > 0 && balance > 0) {
             rate = (supply).div(balance);
        }
        else {
            rate = 1e3;
        }
        return rate;
    }

    // turns ether into weth
    function swapEthtoWeth(uint256 convert) internal {
        if (convert > 0) {
            IWeth(weth).deposit{value: convert}();
        }
    }

    // turns weth into ether
    function swapWethtoEth(uint256 convert) internal {
        if (convert > 0) {
            IWeth(weth).withdraw(convert);
        }
    }

}


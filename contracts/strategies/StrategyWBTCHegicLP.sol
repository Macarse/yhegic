// SPDX-License-Identifier: MIT

pragma experimental ABIEncoderV2;
pragma solidity 0.6.12;

import "@openzeppelinV3/contracts/token/ERC20/IERC20.sol";
import "@openzeppelinV3/contracts/math/SafeMath.sol";
import "@openzeppelinV3/contracts/math/Math.sol";
import "@openzeppelinV3/contracts/utils/Address.sol";
import "@openzeppelinV3/contracts/token/ERC20/SafeERC20.sol";
import {BaseStrategy, StrategyParams} from "@yearnvaults/contracts/BaseStrategy.sol";

import "../../interfaces/hegic/IHegicWbtcPoolStaking.sol";
import "../../interfaces/hegic/IHegicWbtcPool.sol";
import "../../interfaces/uniswap/Uni.sol";

contract StrategyWbtcHegicLP is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    address public wbtc;
    address public rHegic;
    address public wbtcPoolStaking;
    address public wbtcPool;
    address public unirouter;
    string public constant override name = "StrategyWbtcHegicLP";

    constructor(
        address _wbtc,
        address _vault,
        address _rHegic,
        address _wbtcPoolStaking,
        address _wbtcPool,
        address _unirouter
    ) public BaseStrategy(_vault) {
        wbtc = _wbtc;
        rHegic = _rHegic;
        wbtcPoolStaking = _wbtcPoolStaking;
        wbtcPool = _wbtcPool;
        unirouter = _unirouter;

        IERC20(rHegic).safeApprove(unirouter, uint256(-1));
        IERC20(wbtc).safeApprove(wbtcPool, uint256(-1));
        IERC20(wbtcPool).safeApprove(wbtcPoolStaking, uint256(-1));
    }

    function protectedTokens() internal view override returns (address[] memory) {
        address[] memory protected = new address[](3);
        protected[0] = rHegic;
        protected[1] = wbtcPool;
        protected[2] = wbtcPoolStaking;

        return protected;
    }

    function withdrawUnlocked() public view returns (bool) {
        uint256 timeDeposited = IHegicWbtcPool(wbtcPool).lastProvideTimestamp(address(this));
        uint256 timeLock = IHegicWbtcPool(wbtcPool).lockupPeriod();
        return (block.timestamp > timeDeposited.add(timeLock));
    }

    // returns sum of all assets, realized and unrealized
    function estimatedTotalAssets() public view override returns (uint256) {
        return balanceOfWant().add(balanceOfStake()).add(balanceOfPool()).add(wbtcFutureProfit());
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        // We might need to return want to the vault
        if (_debtOutstanding > 0) {
            uint256 _amountFreed = liquidatePosition(_debtOutstanding);
            _debtPayment = Math.min(_amountFreed, _debtOutstanding);
        }

        uint256 balanceOfWantBefore = balanceOfWant();

        // Claim profit only when available
        uint256 rHegicProfit = rHegicFutureProfit();
        if (rHegicProfit > 0) {
            IHegicWbtcPoolStaking(wbtcPoolStaking).getReward();

            // swap rhegic available in the contract for wbtc
            uint256 _rHegicBalance = IERC20(rHegic).balanceOf(address(this));
            _swap(_rHegicBalance);
        }

        // Final profit is want generated in the swap if wbtcProfit > 0
        _profit = balanceOfWant().sub(balanceOfWantBefore);
    }

    // adjusts position.
    function adjustPosition(uint256 _debtOutstanding) internal override {
        //emergency exit is dealt with in prepareReturn
        if (emergencyExit) {
            return;
        }

        // Invest the rest of the want
        uint256 _wantAvailable = balanceOfWant().sub(_debtOutstanding);
        if (_wantAvailable > 0) {
            uint256 _availableFunds = address(this).balance;
            IHegicWbtcPool(wbtcPool).provide(_availableFunds, 0);
            uint256 writeWbtc = IERC20(wbtcPool).balanceOf(address(this));
            IHegicWbtcPoolStaking(wbtcPoolStaking).stake(writeWbtc);
        }
    }

    // N.B. this will only work so long as the various contracts are not timelocked
    // each deposit into the WBTC pool restarts the 14 day counter on the entire value.
    function exitPosition(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        // Shouldn't we revert if we try to exitPosition and there is a timelock?

        uint256 writeWbtc = IHegicWbtcPool(wbtcPool).shareOf(address(this));
        uint256 stakingBalance = IHegicWbtcPoolStaking(wbtcPoolStaking).balanceOf(address(this));

        // by doing this before the timelock check, we will trigger the timelock
        if (stakingBalance > 0) {
            IHegicWbtcPoolStaking(wbtcPoolStaking).exit();
        }

        // timelock will never be negative now that we've changed it to boolean
        bool unlocked = withdrawUnlocked();
        if (unlocked = true) {
            uint256 writeBurn = IERC20(wbtcPool).balanceOf(address(this));
            IHegicWbtcPool(wbtcPool).withdraw(writeWbtc, writeBurn);
            uint256 _wbtcBalance = address(this).balance;
        } else {
            revert("funds timelocked");
        }
    }

    //this math only deals with want, which is wbtc.
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
        uint256 _amountWriteWbtc = (_amount).mul(writeWbtcRatio());
        // this should mean that we always withdraw the amount of writeWbtc we take from staking
        IHegicWbtcPoolStaking(wbtcPoolStaking).withdraw(_amountWriteWbtc);
        uint256 _amountBurn = IERC20(wbtcPool).balanceOf(address(this));
        bool unlocked = withdrawUnlocked();
        if (unlocked = true) {
            IHegicWbtcPool(wbtcPool).withdraw(_amount, _amountBurn);
        } else {
            revert("withdrawal timelocked");
        }
    }

    // this function transfers not just "want" tokens, but all tokens - including (un)staked writeWbtc.
    function prepareMigration(address _newStrategy) internal override {
        want.transfer(_newStrategy, balanceOfWant());
        IERC20(wbtcPool).transfer(_newStrategy, IERC20(wbtcPool).balanceOf(address(this)));
        IERC20(wbtcPoolStaking).transfer(_newStrategy, IERC20(wbtcPoolStaking).balanceOf(address(this)));
    }

    // swaps rHegic for wbtc
    function _swap(uint256 _amountIn) internal returns (uint256[] memory amounts) {
        address[] memory path = new address[](2);
        path[0] = address(0x47C0aD2aE6c0Ed4bcf7bc5b380D7205E89436e84); // rHegic
        path[1] = address(want);

        Uni(unirouter).swapExactTokensForTokens(_amountIn, uint256(0), path, address(this), now.add(1 days));
    }

    // calculates the Wbtc that earned rHegic is worth
    function wbtcFutureProfit() public view returns (uint256) {
        uint256 rHegicProfit = rHegicFutureProfit();
        if (rHegicProfit == 0) {
            return 0;
        }

        address[] memory path = new address[](2);
        path[0] = address(0x47C0aD2aE6c0Ed4bcf7bc5b380D7205E89436e84); // rHegic
        path[1] = address(want);
        uint256[] memory amounts = Uni(unirouter).getAmountsOut(rHegicProfit, path);

        return amounts[amounts.length - 1];
    }

    // returns (r)Hegic earned by the LP
    function rHegicFutureProfit() public view returns (uint256) {
        return IHegicWbtcPoolStaking(wbtcPoolStaking).earned(address(this));
    }

    // returns wbtc in the pool
    function balanceOfPool() internal view returns (uint256) {
        uint256 ratio = writeWbtcRatio();
        uint256 writeWbtc = IERC20(wbtcPool).balanceOf(address(this));
        return (writeWbtc).div(ratio);
    }

    // returns pooled Wbtc that is staked
    function balanceOfStake() internal view returns (uint256) {
        uint256 ratio = writeWbtcRatio();
        uint256 writeWbtc = IERC20(wbtcPoolStaking).balanceOf(address(this));
        return (writeWbtc).div(ratio);
    }

    // returns balance of wbtc
    function balanceOfWant() public view returns (uint256) {
        return IERC20(want).balanceOf(address(this));
    }

    // calculates the current wbtc:writeWbtc ratio. Should return approx ~1000
    function writeWbtcRatio() internal view returns (uint256) {
        uint256 supply = IHegicWbtcPool(wbtcPool).totalSupply();
        uint256 balance = IHegicWbtcPool(wbtcPool).totalBalance();
        uint256 rate = 0;
        if (supply > 0 && balance > 0) {
            rate = (supply).div(balance);
        } else {
            rate = 1e3;
        }
        return rate;
    }

    // calculates rewards rate in tokens per year for this address
    function calculateRate() public view returns (uint256) {
        uint256 rate = IHegicWbtcPoolStaking(wbtcPoolStaking).userRewardPerTokenPaid(address(this));
        uint256 supply = IHegicWbtcPoolStaking(wbtcPoolStaking).totalSupply();
        uint256 ROI = IERC20(wbtcPoolStaking).balanceOf(address(this)).div(supply).mul(rate).mul((31536000));
        return ROI;
    }
}

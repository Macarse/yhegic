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
        address _weth
        address _vault,
        address _hegic,
        address _rHegic,
        address _EthPoolStaking,
        address _EthPool,
        address _unirouter,
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

    function timelockRemaining() internal view returns (uint256) {
        uint256 timeDeposited = IHegicEthPool(EthPool).lastProvideTimestamp(address(this));
        uint256 timeLock = IHegicEthPool(EthPool).lockupPeriod();
        uint256 timeUnlocked = block.timestamp;

        return (timeUnlocked).sub((timeLock).add(timeDeposited));
    }


    // returns sum of all assets, realized and unrealized
    function estimatedTotalAssets() public override view returns (uint256) {
        return balanceOfWant(address(this)).add(balanceOfStake()).add(balanceOfPool()).add(ethFutureProfit());
    }

    // TODO: this entire function
    function prepareReturn(uint256 _debtOutstanding) internal override returns (uint256 _profit) {
        // We might need to return want to the vault
        if (_debtOutstanding > 0) {
            liquidatePosition(_debtOutstanding);
        }

        // Update reserve with the available want so it's not considered profit
        setReserve(balanceOfWant().sub(_debtOutstanding));

        // Claim profit only when available
        uint256 wbtcProfit = wbtcFutureProfit();
        if (wbtcProfit > 0) {
            IHegicStaking(hegicStaking).claimProfit();

            // swap wbtc available in the contract for hegic
            uint256 _wbtcBalance = IERC20(WBTC).balanceOf(address(this));
            _swap(_wbtcBalance);
        }

        // Final profit is want generated in the swap if ethProfit > 0
        _profit = balanceOfWant().sub(getReserve());
    }


    //TODO: this entire function - this is the new "deposit" function
    function adjustPosition(uint256 _debtOutstanding) internal override {
        //emergency exit is dealt with in prepareReturn
        if (emergencyExit) {
            return;
        }

        // Reset the reserve value before
        setReserve(0);

        // Invest the rest of the want
        uint256 _wantAvailable = balanceOfWant().sub(_debtOutstanding);
        uint256 _lotsToBuy = _wantAvailable.div(LOT_PRICE);

        if (_lotsToBuy > 0) {
            IHegicStaking(hegicStaking).buy(_lotsToBuy);
        }
    }

    // N.B. this will only work so long as the various contracts are not timelocked
    // each deposit into the ETH pool restarts the 14 day counter on the entire value.
        // TODO: we will have to include a deposit lockout for lockupPeriod()+1 days imo to allow exiting position
        // TODO: include eth->weth conversion
    function exitPosition() internal override {
        uint256 stakes = IERC20(EthPoolStaking).balanceOf(address(this));
        uint256 writeEth = IERC20(EthPool).balanceOf(address(this));
        if timeLockRemaining() <= 0 {
            IHegicEthPoolStaking(EthPoolStaking).exit();
            IHegicEthPool(EthPool).withdraw(writeEth);
        }
        else return name = "withdrawal timelocked";
    }

    //TODO: This entire function. It seems... identical to above, yeah?
    function liquidatePosition(uint256 _amountNeeded) internal override returns (uint256 _amountFreed) {
        if (balanceOfWant() < _amountNeeded) {
            // We need to sell stakes to get back more want
            _withdrawSome(_amountNeeded.sub(balanceOfWant()));
        }

        // Since we might free more than needed, let's send back the min
        _amountFreed = Math.min(balanceOfWant(), _amountNeeded);
    }


    //TODO: This function
    function _withdrawSome(uint256 _amount) internal returns (uint256) {
        uint256 _amountWriteEth = (_amount).mul(writeEthRatio());

        if timeLockRemaining() <= 0 {
            IHegicEthPoolStaking(EthPoolStaking).withdraw(_amount.div())
            // IHegicEthPoolStaking(EthPoolStaking).exit();
            //IHegicEthPool(EthPool).withdraw(writeEth);
        }
        else return name = "withdrawal timelocked";


        //uint256 stakesToSell = 0;
        //if (_amount.mod(LOT_PRICE) == 0) {
        //    stakesToSell = _amount.div(LOT_PRICE);
        //} else {
            // **If there is a remainder, we need to sell one more lot to cover
        //    stakesToSell = _amount.div(LOT_PRICE).add(1);
        //}

        // sell might fail if we hit the 24hs lock
       // IHegicStaking(hegicStaking).sell(stakesToSell);
        //return stakesToSell.mul(LOT_PRICE);
    }


    //TODO: This entire function
    function prepareMigration(address _newStrategy) internal override {
        want.transfer(_newStrategy, balanceOfWant());
        IERC20(hegicStaking).transfer(_newStrategy, IERC20(hegicStaking).balanceOf(address(this)));
    }

    //TODO: This entire function
    function _swap(uint256 _amountIn) internal returns (uint256[] memory amounts) {
        address[] memory path = new address[](3);
        path[0] = address(0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599); // wbtc
        path[1] = address(0x6B175474E89094C44Da98b954EedeAC495271d0F); // dai
        path[2] = address(want);

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
        if (supply > 0 && balance > 0)
            uint256 rate = (supply).div(balance);
        else
            uint256 rate = 1e3;
        return rate;
    }

    function swapEthtoWeth() internal {}

}


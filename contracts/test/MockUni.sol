// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "./FakeHegic.sol";

contract MockUni {
    FakeHegic token;
    uint256 hegicPrice = 325020000000000; // 0.13 usd / 0.00032502 ether

    constructor(FakeHegic _token) public {
        token = _token;
    }

    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external {
      token.mintTo(to, 2* 10**18);
    }

    function swapExactETHForTokens(
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external payable returns (uint256[] memory amounts) {
        require(path[0] == address(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2), "weth");
        uint256 convertedAmount = (amountOutMin / hegicPrice) * 10**18;
        token.mintTo(to, convertedAmount);

        amounts = new uint256[](2);
        amounts[0] = 1;
        amounts[1] = convertedAmount;

        return amounts;
    }

    function getAmountsOut(uint256 amountIn, address[] memory path) external view returns (uint256[] memory amounts) {
        if (amountIn == 0) {
            revert("UniswapV2Library: INSUFFICIENT_INPUT_AMOUNT");
        }

        require(path[0] == address(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2), "weth");
        amounts = new uint256[](2);
        amounts[0] = 0;
        amounts[1] = (amountIn / hegicPrice) * 10**18;
    }
}

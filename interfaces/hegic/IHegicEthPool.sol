// SPDX-License-Identifier: MIT

pragma solidity ^0.6.12;

interface IHegicEthPool {
    function approve(address, uint256);

    function provide(uint256) external payable returns (uint256);

    function withdraw (uint256, uint256) external returns (uint256);

    function shareOf(address) external view returns (uint256);

    function availableBalance() public view returns (uint256);

    function totalBalance() public override view returns (uint256);

    function totalSupply() public override view returns (uint256);

    function lastProvideTimestamp(address) public view returns (uint256);

    function lockupPeriod() public view returns (uint256);

}

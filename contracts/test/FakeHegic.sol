// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "@openzeppelinV3/contracts/token/ERC20/ERC20.sol";

contract FakeHegic is ERC20 {
    constructor() public ERC20("HEGIC fake token", "fHEGIC") {
        _mint(msg.sender, 300_000_000 * 10**18);
    }

    function mintTo(address account, uint256 amount) public {
        _mint(account, amount);
    }
}

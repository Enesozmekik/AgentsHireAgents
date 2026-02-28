// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IAmeWithdraw {
    function withdrawFees(address payable to, uint256 amount) external;
}

contract ReentrantWithdrawAttacker {
    IAmeWithdraw public immutable target;
    uint256 public attackAmount;
    bool public attemptedReentry;

    constructor(address targetAddress) {
        target = IAmeWithdraw(targetAddress);
    }

    function attack(uint256 amount) external {
        attackAmount = amount;
        target.withdrawFees(payable(address(this)), amount);
    }

    receive() external payable {
        if (!attemptedReentry) {
            attemptedReentry = true;
            // Try to drain fees recursively; nonReentrant in target should block this.
            try target.withdrawFees(payable(address(this)), attackAmount) {} catch {}
        }
    }
}

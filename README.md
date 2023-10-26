# t_balance
Targeted balance using python-btrfs

simple_reclaim just selects chunks that aren't on your under-used device and balances them.

reclaim tries to be a bit cleverer and picks pairs which will restore the unallocatable space with fewer writes.

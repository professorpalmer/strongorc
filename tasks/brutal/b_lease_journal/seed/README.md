# holdbook

A lease is a timestamped mutex. Whoever has the newest timestamp owns the key. Expiring a lease resets the generation to 0 so the next owner starts fresh.

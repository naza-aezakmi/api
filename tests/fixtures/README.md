Public NASA data fixtures, fetched 2026-11-15:

- `power_climatology.json`: NASA POWER point climatology at 31.701° N, 59.352° E, parameters T2M, TS, T2M_MIN, T2M_MAX, PRECTOTCORR, RH2M, WS10M, PS. https://power.larc.nasa.gov/api/temporal/climatology/point . Only the supported six mean variables and twelve monthly T2M means enter the passport.
- `diviner_apollo_cell.txt`: 96 × 113 byte records from the NASA PDS Diviner Global Cumulative Product `global_cumul_avg_cyl_00n10n_002.tab`, bin 0.75° N, 23.25° E. Byte range starts at `113 + (406 * 20 + 1) * 96 * 113`. https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gcp/ . Data cover observations 2009-07-05 to 2015-04-01; missing values are preserved.

-- Delete dispatcher log and log codes
DELETE from fledge.log WHERE code = 'DSPST';
DELETE from fledge.log_codes WHERE code = 'DSPST';
DELETE from fledge.log WHERE code = 'DSPSD';
DELETE from fledge.log_codes WHERE code = 'DSPSD';

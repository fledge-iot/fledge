-- Delete Audit marker log and log codes entry
DELETE from fledge.log WHERE code = 'AUMRK';
DELETE from fledge.log_codes WHERE code = 'AUMRK';

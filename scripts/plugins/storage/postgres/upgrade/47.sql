-- Scheduled process entry for automation script task

INSERT INTO fledge.scheduled_processes SELECT 'automation_script', '["tasks/automation_script"]' WHERE NOT EXISTS (SELECT 1 FROM fledge.scheduled_processes WHERE name = 'automation_script');
